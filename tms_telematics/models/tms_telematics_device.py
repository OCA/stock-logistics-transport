# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class TmsTelematicsDevice(models.Model):
    _name = "tms.telematics.device"
    _description = "Telematics Device"
    _order = "name, id"

    name = fields.Char(required=True)
    account_id = fields.Many2one(
        "tms.telematics.account",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(related="account_id.company_id", store=True)
    external_id = fields.Char(required=True, index=True)
    vehicle_id = fields.Many2one("fleet.vehicle", string="Vehicle", index=True)
    vin = fields.Char(string="VIN")
    license_plate = fields.Char()
    last_latitude = fields.Float(digits=(10, 6))
    last_longitude = fields.Float(digits=(10, 6))
    last_position_date = fields.Datetime()
    last_speed = fields.Float(string="Last speed (km/h)")
    last_ignition = fields.Selection(
        [("on", "On"), ("off", "Off")],
        string="Last ignition",
    )
    last_odometer_km = fields.Float(string="Last odometer (km)")
    reading_ids = fields.One2many("tms.telematics.reading", "device_id")

    _account_external_uniq = models.Constraint(
        "unique (account_id, external_id)",
        "This device was already imported on the account.",
    )

    def _match_vehicle(self, vin=None, plate=None):
        """Link the device to a vehicle by the existing link, then VIN, then plate."""
        self.ensure_one()
        if self.vehicle_id:
            return self.vehicle_id
        vehicle = self.env["fleet.vehicle"]
        company_ids = [False, self.company_id.id]
        if vin:
            vehicle = vehicle.sudo().search(
                [("vin_sn", "=", vin), ("company_id", "in", company_ids)],
                limit=1,
            )
        if not vehicle and plate:
            vehicle = self.env["fleet.vehicle"].sudo().search(
                [
                    ("license_plate", "=", plate),
                    ("company_id", "in", company_ids),
                ],
                limit=1,
            )
        if vehicle:
            self.vehicle_id = vehicle
        return self.vehicle_id
