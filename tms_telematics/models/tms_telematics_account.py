# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import secrets
from datetime import datetime, timezone

from dateutil.parser import isoparse

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare

_logger = logging.getLogger(__name__)

KM_PER_MILE = 1.609344


def as_utc_naive(value):
    """Return a naive UTC datetime, or False when the value cannot be parsed."""
    if not value:
        return False
    if isinstance(value, datetime):
        moment = value
    else:
        try:
            moment = isoparse(str(value))
        except (TypeError, ValueError):
            return False
    if moment.tzinfo:
        moment = moment.astimezone(timezone.utc).replace(tzinfo=None)
    return moment


class TmsTelematicsAccount(models.Model):
    _name = "tms.telematics.account"
    _description = "Telematics Account"
    _order = "name, id"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    provider = fields.Selection(selection=lambda self: self._selection_provider())
    server_url = fields.Char(string="Server")
    database_name = fields.Char(string="Database")
    login = fields.Char()
    password = fields.Char(groups="tms.group_tms_admin", copy=False)
    session_id = fields.Char(groups="tms.group_tms_admin", copy=False)
    session_server = fields.Char(groups="tms.group_tms_admin", copy=False)
    session_expires = fields.Datetime(groups="tms.group_tms_admin", copy=False)
    feed_cursor = fields.Text(copy=False)
    webhook_token = fields.Char(
        default=lambda self: secrets.token_urlsafe(24),
        copy=False,
        groups="tms.group_tms_admin",
    )
    last_sync = fields.Datetime(readonly=True)
    device_ids = fields.One2many("tms.telematics.device", "account_id")
    reading_ids = fields.One2many("tms.telematics.reading", "account_id")
    reading_count = fields.Integer(compute="_compute_reading_count")

    @api.model
    def _selection_provider(self):
        return []

    @api.depends("reading_ids")
    def _compute_reading_count(self):
        for account in self:
            account.reading_count = len(account.reading_ids)

    def action_view_readings(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Readings"),
            "res_model": "tms.telematics.reading",
            "view_mode": "list,form",
            "domain": [("account_id", "=", self.id)],
        }

    def action_pull(self):
        self._enqueue_pull()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "message": self.env._("The pull was queued."),
                "type": "success",
                "sticky": False,
            },
        }

    def _enqueue_pull(self):
        for account in self:
            account.with_delay(
                channel="root.telematics",
                description=self.env._("Telematics pull %(name)s", name=account.name),
            )._pull()

    @api.model
    def _cron_pull(self):
        self.search([("active", "=", True)])._enqueue_pull()

    def _pull(self):
        for account in self:
            readings, cursor = account._pull_readings()
            account.apply_readings(readings)
            vals = {"last_sync": fields.Datetime.now()}
            if cursor is not None:
                vals["feed_cursor"] = cursor
            account.write(vals)
            _logger.info(
                "Telematics account %s imported %s readings",
                account.id,
                len(readings or []),
            )

    def _pull_readings(self):
        self.ensure_one()
        if not self.provider:
            raise UserError(self.env._("Set a provider before pulling this account."))
        method = getattr(self, "_pull_%s" % self.provider, None)
        if not method:
            raise UserError(
                self.env._(
                    "Provider %(provider)s has no pull method.",
                    provider=self.provider,
                )
            )
        return method()

    def _accept_webhook(self, token, payload):
        self.ensure_one()
        if not token or token != self.webhook_token:
            return {"error": "forbidden"}
        if isinstance(payload, list):
            readings = payload
        elif isinstance(payload, dict):
            readings = payload.get("readings")
        else:
            return {"error": "invalid"}
        if not isinstance(readings, list):
            return {"error": "invalid"}
        self.with_delay(
            channel="root.telematics",
            description=self.env._("Telematics webhook"),
        )._apply_readings_job(readings)
        return {"queued": len(readings)}

    def _apply_readings_job(self, readings):
        self.ensure_one()
        self.apply_readings(readings)

    def apply_readings(self, readings):
        """Store new readings and update the vehicle, the trip, and the position.

        ``readings`` is a list of dicts. Distances are kilometers. Each item
        needs ``external_id`` and ``device_external_id``. ``event`` is one of
        ``position``, ``trip_start``, ``trip_end``, and ``fill``.
        """
        self.ensure_one()
        payloads = [row for row in (readings or []) if row.get("external_id")]
        known = set(
            self.env["tms.telematics.reading"]
            .search(
                [
                    ("account_id", "=", self.id),
                    ("external_id", "in", [row["external_id"] for row in payloads]),
                ]
            )
            .mapped("external_id")
        )
        created = self.env["tms.telematics.reading"]
        devices = {}
        for payload in payloads:
            if payload["external_id"] in known:
                continue
            device_external_id = payload.get("device_external_id")
            if not device_external_id:
                continue
            device = devices.get(device_external_id)
            if not device:
                device = self._ensure_device(payload)
                devices[device_external_id] = device
            reading = self._create_reading(device, payload)
            known.add(reading.external_id)
            created |= reading
            self._apply_reading(device, reading)
        return created

    def _ensure_device(self, payload):
        self.ensure_one()
        external_id = payload.get("device_external_id") or payload.get("external_id")
        device = self.env["tms.telematics.device"].search(
            [("account_id", "=", self.id), ("external_id", "=", external_id)],
            limit=1,
        )
        vals = {}
        name = payload.get("device_name") or payload.get("name")
        vin = payload.get("vin")
        plate = payload.get("license_plate")
        if name and (not device or not device.name):
            vals["name"] = name
        if vin and (not device or not device.vin):
            vals["vin"] = vin
        if plate and (not device or not device.license_plate):
            vals["license_plate"] = plate
        if device:
            if vals:
                device.write(vals)
        else:
            vals.update(
                {
                    "account_id": self.id,
                    "external_id": external_id,
                    "name": name or external_id,
                }
            )
            device = self.env["tms.telematics.device"].create(vals)
        device._match_vehicle(vin or device.vin, plate or device.license_plate)
        return device

    def _sync_devices(self, rows):
        """Create or update devices from a provider's device catalog."""
        self.ensure_one()
        for row in rows or []:
            if row.get("external_id"):
                self._ensure_device(
                    {
                        "device_external_id": row["external_id"],
                        "device_name": row.get("name"),
                        "vin": row.get("vin"),
                        "license_plate": row.get("license_plate"),
                    }
                )

    def _create_reading(self, device, payload):
        ignition = payload.get("ignition")
        if ignition is True:
            ignition_value = "on"
        elif ignition is False:
            ignition_value = "off"
        else:
            ignition_value = False
        latitude = payload.get("latitude")
        longitude = payload.get("longitude")
        speed = payload.get("speed")
        return self.env["tms.telematics.reading"].create(
            {
                "account_id": self.id,
                "device_id": device.id,
                "external_id": payload["external_id"],
                "event": payload.get("event") or "position",
                "timestamp": as_utc_naive(payload.get("timestamp")),
                "latitude": latitude or 0.0,
                "longitude": longitude or 0.0,
                "position_set": latitude is not None and longitude is not None,
                "odometer_km": payload.get("odometer_km") or 0.0,
                "speed": speed if speed is not None and speed >= 0 else 0.0,
                "speed_known": speed is not None and speed >= 0,
                "ignition": ignition_value,
                "fuel_liters": payload.get("fuel_liters") or 0.0,
            }
        )

    def _apply_reading(self, device, reading):
        self._update_position(device, reading)
        assigned = False
        if reading.event in ("trip_start", "trip_end"):
            assigned = self._assign_trip_reading(device, reading)
        if reading.odometer_km and not assigned:
            self._record_odometer(device, reading)
        if reading.event == "fill":
            self._apply_fill(reading)
        if reading.odometer_km:
            device.last_odometer_km = reading.odometer_km

    def _update_position(self, device, reading):
        if not reading.position_set:
            return
        if (
            device.last_position_date
            and reading.timestamp
            and reading.timestamp < device.last_position_date
        ):
            return
        vals = {
            "last_latitude": reading.latitude,
            "last_longitude": reading.longitude,
            "last_position_date": reading.timestamp,
        }
        if reading.speed_known:
            vals["last_speed"] = reading.speed
        if reading.ignition:
            vals["last_ignition"] = reading.ignition
        device.write(vals)

    def _open_trip_domain(self, vehicle):
        return [
            ("vehicle_id", "=", vehicle.id),
            "|",
            ("stage_id", "=", False),
            "&",
            ("stage_id.fold", "=", False),
            ("stage_id.is_completed", "=", False),
        ]

    def _assign_trip_reading(self, device, reading):
        vehicle = device.vehicle_id
        if not vehicle or not reading.odometer_km:
            return False
        domain = self._open_trip_domain(vehicle)
        if reading.event == "trip_start":
            domain.append(("odometer_start_id", "=", False))
            field = "odometer_start"
        else:
            domain.extend(
                [
                    ("odometer_start_id", "!=", False),
                    ("odometer_end_id", "=", False),
                ]
            )
            field = "odometer_end"
        trip = self.env["tms.order"].search(domain, order="id", limit=1)
        if not trip:
            return False
        value = self._to_vehicle_unit(vehicle, reading.odometer_km)
        if not self._odometer_value_fits(trip, field, value):
            return False
        vals = {field: value}
        if field == "odometer_start" and not trip.date_start and reading.timestamp:
            vals["date_start"] = reading.timestamp
        if field == "odometer_end" and reading.timestamp:
            vals["date_end"] = reading.timestamp
        trip.sudo().write(vals)
        return True

    def _odometer_value_fits(self, trip, field, value):
        start = value if field == "odometer_start" else trip.odometer_start
        end = value if field == "odometer_end" else trip.odometer_end
        if end and start and end < start:
            return False
        split = trip.distance_loaded + trip.distance_empty
        if end and start and split and abs(split - (end - start)) > 0.01:
            return False
        return True

    def _record_odometer(self, device, reading):
        vehicle = device.vehicle_id
        if not vehicle:
            return False
        value = self._to_vehicle_unit(vehicle, reading.odometer_km)
        moment = reading.timestamp or fields.Datetime.now()
        reading_date = fields.Date.to_date(moment)
        last = self.env["fleet.vehicle.odometer"].search(
            [("vehicle_id", "=", vehicle.id)],
            order="date desc, id desc",
            limit=1,
        )
        moved = not last or float_compare(last.value, value, precision_digits=1) != 0
        if not moved and reading.ignition != "off":
            return False
        if not moved and last and last.date == reading_date:
            return False
        self.env["fleet.vehicle.odometer"].sudo().create(
            {
                "vehicle_id": vehicle.id,
                "value": value,
                "date": reading_date,
            }
        )
        return True

    def _to_vehicle_unit(self, vehicle, kilometers):
        if vehicle.odometer_unit == "miles":
            return kilometers / KM_PER_MILE
        return kilometers

    def _apply_fill(self, reading):
        """Hook for a module that turns a fill into an expense."""
        return True
