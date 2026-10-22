# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.http import Response
from odoo.tests.common import TransactionCase

from odoo.addons.tms_telematics.controllers.webhook import TmsTelematicsHook


class _Delay:
    def __init__(self, record, bucket):
        self.record = record
        self.bucket = bucket

    def _pull(self):
        self.bucket["pull"] = self.bucket.get("pull", 0) + 1

    def _apply_readings_job(self, readings):
        self.bucket["readings"] = readings


class TestTelematics(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        brand = cls.env["fleet.vehicle.model.brand"].create({"name": "Telematics"})
        model = cls.env["fleet.vehicle.model"].create(
            {"name": "Tracker", "brand_id": brand.id}
        )
        cls.model = model
        cls.vehicle = cls.env["fleet.vehicle"].create(
            {
                "model_id": model.id,
                "license_plate": "TEL-001",
                "vin_sn": "VIN-TEL-001",
                "odometer_unit": "kilometers",
            }
        )
        cls.account = cls.env["tms.telematics.account"].create({"name": "Feed"})

    def _vehicle(self, plate, vin=None, unit="kilometers"):
        vals = {
            "model_id": self.model.id,
            "license_plate": plate,
            "odometer_unit": unit,
        }
        if vin:
            vals["vin_sn"] = vin
        return self.env["fleet.vehicle"].create(vals)

    def _patch_delay(self, bucket):
        def _with_delay(record, *args, **kwargs):
            bucket["channel"] = kwargs.get("channel")
            return _Delay(record, bucket)

        return patch.object(type(self.account), "with_delay", _with_delay, create=True)

    def _reading(self, **extra):
        payload = {
            "external_id": "r1",
            "device_external_id": "d1",
            "device_name": "Tracker",
            "event": "position",
            "timestamp": "2026-09-10T15:00:00Z",
            "latitude": 25.68,
            "longitude": -100.31,
            "speed": 80,
        }
        payload.update(extra)
        return payload

    def test_position_links_by_vin_and_ignores_a_duplicate(self):
        created = self.account.apply_readings(
            [self._reading(vin="VIN-TEL-001", ignition=True)]
        )
        self.assertEqual(len(created), 1)
        device = created.device_id
        self.assertEqual(device.vehicle_id, self.vehicle)
        self.assertEqual(device.last_latitude, 25.68)
        self.assertEqual(device.last_speed, 80)
        self.assertEqual(device.last_ignition, "on")
        self.assertFalse(
            self.env["fleet.vehicle.odometer"].search_count(
                [("vehicle_id", "=", self.vehicle.id)]
            )
        )
        again = self.account.apply_readings([self._reading(vin="VIN-TEL-001")])
        self.assertFalse(again)
        self.assertEqual(created.timestamp.hour, 15)

    def test_plate_is_used_when_the_vin_is_unknown(self):
        created = self.account.apply_readings(
            [self._reading(vin="MISSING", license_plate="TEL-001")]
        )
        self.assertEqual(created.device_id.vehicle_id, self.vehicle)

    def test_an_existing_vehicle_link_is_kept(self):
        other = self._vehicle("TEL-002", vin="VIN-OTHER")
        self.account.apply_readings([self._reading(vin="VIN-TEL-001")])
        created = self.account.apply_readings(
            [self._reading(external_id="r2", vin=other.vin_sn)]
        )
        self.assertEqual(created.device_id.vehicle_id, self.vehicle)

    def test_older_position_does_not_replace_the_latest(self):
        self.account.apply_readings([self._reading()])
        self.account.apply_readings(
            [
                self._reading(
                    external_id="older",
                    timestamp="2026-09-10T14:00:00Z",
                    latitude=1,
                    longitude=2,
                    speed=10,
                )
            ]
        )
        device = self.account.device_ids
        self.assertEqual(device.last_latitude, 25.68)
        self.assertEqual(device.last_speed, 80)

    def test_zero_coordinates_are_stored(self):
        created = self.account.apply_readings(
            [self._reading(latitude=0, longitude=0, speed=None)]
        )
        self.assertTrue(created.position_set)
        self.assertEqual(created.device_id.last_latitude, 0)
        self.assertFalse(created.speed_known)

    def test_invalid_timestamp_is_empty(self):
        created = self.account.apply_readings([self._reading(timestamp="not-a-date")])
        self.assertFalse(created.timestamp)

    def test_trip_boundaries_write_fleet_readings(self):
        trip = self.env["tms.order"].create(
            {"name": "TEL/1", "vehicle_id": self.vehicle.id}
        )
        self.account.apply_readings(
            [
                self._reading(
                    external_id="start",
                    event="trip_start",
                    odometer_km=1000,
                    vin="VIN-TEL-001",
                    timestamp="2026-09-10T08:00:00Z",
                )
            ]
        )
        self.assertEqual(trip.odometer_start, 1000)
        self.assertEqual(trip.odometer_start_id.vehicle_id, self.vehicle)
        self.assertEqual(trip.date_start.hour, 8)
        self.account.apply_readings(
            [
                self._reading(
                    external_id="end",
                    event="trip_end",
                    odometer_km=1100,
                    timestamp="2026-09-10T12:00:00Z",
                    ignition=False,
                )
            ]
        )
        self.assertEqual(trip.odometer_end, 1100)
        self.assertEqual(trip.date_end.hour, 12)
        self.assertEqual(
            self.env["fleet.vehicle.odometer"].search_count(
                [("vehicle_id", "=", self.vehicle.id)]
            ),
            2,
        )

    def test_arrival_below_departure_is_not_written_on_the_trip(self):
        trip = self.env["tms.order"].create(
            {"name": "TEL/LOW", "vehicle_id": self.vehicle.id}
        )
        self.account.apply_readings(
            [
                self._reading(
                    external_id="start",
                    event="trip_start",
                    odometer_km=1000,
                    vin="VIN-TEL-001",
                )
            ]
        )
        self.account.apply_readings(
            [self._reading(external_id="end", event="trip_end", odometer_km=900)]
        )
        self.assertFalse(trip.odometer_end)

    def test_a_split_that_does_not_match_skips_the_trip(self):
        trip = self.env["tms.order"].create(
            {
                "name": "TEL/SPLIT",
                "vehicle_id": self.vehicle.id,
                "distance_loaded": 10,
            }
        )
        self.account.apply_readings(
            [
                self._reading(
                    external_id="start",
                    event="trip_start",
                    odometer_km=1000,
                    vin="VIN-TEL-001",
                )
            ]
        )
        self.account.apply_readings(
            [self._reading(external_id="end", event="trip_end", odometer_km=1200)]
        )
        self.assertFalse(trip.odometer_end)

    def test_completed_and_cancelled_trips_are_left_alone(self):
        completed = self.env["tms.stage"].search(
            [("stage_type", "=", "order"), ("is_completed", "=", True)],
            limit=1,
        )
        cancelled = self.env["tms.stage"].search(
            [("stage_type", "=", "order"), ("fold", "=", True)],
            limit=1,
        )
        done = self.env["tms.order"].create(
            {
                "name": "TEL/DONE",
                "vehicle_id": self.vehicle.id,
                "stage_id": completed.id,
            }
        )
        closed = self.env["tms.order"].create(
            {
                "name": "TEL/CANCEL",
                "vehicle_id": self.vehicle.id,
                "stage_id": cancelled.id,
            }
        )
        open_trip = self.env["tms.order"].create(
            {"name": "TEL/OPEN", "vehicle_id": self.vehicle.id}
        )
        self.account.apply_readings(
            [
                self._reading(
                    event="trip_start",
                    odometer_km=500,
                    vin="VIN-TEL-001",
                )
            ]
        )
        self.assertFalse(done.odometer_start)
        self.assertFalse(closed.odometer_start)
        self.assertEqual(open_trip.odometer_start, 500)

    def test_miles_are_converted_before_the_fleet_log(self):
        vehicle = self._vehicle("TEL-MI", vin="VIN-MILES", unit="miles")
        self.account.apply_readings(
            [
                self._reading(
                    event="position",
                    odometer_km=1.609344,
                    vin="VIN-MILES",
                    ignition=False,
                )
            ]
        )
        log = self.env["fleet.vehicle.odometer"].search(
            [("vehicle_id", "=", vehicle.id)]
        )
        self.assertAlmostEqual(log.value, 1.0, places=4)

    def test_ignition_off_does_not_repeat_the_same_reading(self):
        self.account.apply_readings(
            [
                self._reading(
                    odometer_km=100,
                    vin="VIN-TEL-001",
                    ignition=False,
                )
            ]
        )
        self.account.apply_readings(
            [
                self._reading(
                    external_id="again",
                    odometer_km=100,
                    ignition=False,
                )
            ]
        )
        self.assertEqual(
            self.env["fleet.vehicle.odometer"].search_count(
                [("vehicle_id", "=", self.vehicle.id)]
            ),
            1,
        )

    def test_a_reading_without_a_vehicle_does_not_write_the_odometer(self):
        before = self.env["fleet.vehicle.odometer"].search_count([])
        created = self.account.apply_readings(
            [self._reading(odometer_km=40, license_plate="UNKNOWN")]
        )
        self.assertFalse(created.device_id.vehicle_id)
        self.assertEqual(self.env["fleet.vehicle.odometer"].search_count([]), before)

    def test_fill_calls_the_hook(self):
        called = {}

        def _apply_fill(record, reading):
            called["liters"] = reading.fuel_liters
            return True

        payload = self._reading(event="fill", fuel_liters=40, odometer_km=10)
        with patch.object(type(self.account), "_apply_fill", _apply_fill):
            created = self.account.apply_readings([payload])
        self.assertEqual(created.event, "fill")
        self.assertEqual(called["liters"], 40)
        self.assertEqual(self.account.reading_count, 1)

    def test_incomplete_payloads_are_skipped(self):
        created = self.account.apply_readings(
            [{"external_id": "x"}, {"device_external_id": "d"}, {}]
        )
        self.assertFalse(created)

    def test_pull_requires_a_provider(self):
        with self.assertRaises(UserError):
            self.account._pull_readings()

    def test_pull_requires_a_provider_method(self):
        self.env.cr.execute(
            "UPDATE tms_telematics_account SET provider = %s WHERE id = %s",
            ("orphan", self.account.id),
        )
        self.account.invalidate_recordset()
        with self.assertRaises(UserError):
            self.account._pull_readings()

    def test_cron_queues_only_active_accounts(self):
        self.env["tms.telematics.account"].create({"name": "Paused", "active": False})
        bucket = {}
        with self._patch_delay(bucket):
            self.env["tms.telematics.account"]._cron_pull()
        self.assertEqual(bucket["pull"], 1)
        self.assertEqual(bucket["channel"], "root.telematics")

    def test_pull_button_notifies(self):
        bucket = {}
        with self._patch_delay(bucket):
            action = self.account.action_pull()
        self.assertEqual(action["tag"], "display_notification")
        self.assertEqual(bucket["pull"], 1)
        readings = self.account.action_view_readings()
        self.assertEqual(readings["domain"], [("account_id", "=", self.account.id)])

    def test_webhook_queues_a_list_and_rejects_a_bad_token(self):
        bucket = {}
        payload = [self._reading()]
        with self._patch_delay(bucket):
            denied = self.account._accept_webhook("nope", {"readings": payload})
            queued = self.account._accept_webhook(
                self.account.webhook_token, {"readings": payload}
            )
            listed = self.account._accept_webhook(self.account.webhook_token, payload)
        self.assertEqual(denied, {"error": "forbidden"})
        self.assertEqual(queued["queued"], 1)
        self.assertEqual(listed["queued"], 1)
        self.assertEqual(bucket["channel"], "root.telematics")
        self.account._apply_readings_job(bucket["readings"])
        self.assertEqual(self.account.reading_count, 1)

    def test_webhook_rejects_a_payload_that_is_not_a_list(self):
        result = self.account._accept_webhook(
            self.account.webhook_token, {"readings": 1}
        )
        self.assertEqual(result, {"error": "invalid"})
        result = self.account._accept_webhook(self.account.webhook_token, "text")
        self.assertEqual(result, {"error": "invalid"})

    def test_hook_route(self):
        bucket = {}
        controller = TmsTelematicsHook()
        request = type("Request", (), {})()
        request.env = self.env
        request.httprequest = type("Http", (), {})()
        request.httprequest.headers = {"X-Telematics-Token": self.account.webhook_token}
        request.httprequest.data = b'{"readings": []}'

        def make_json_response(body, status=200):
            return Response(
                json.dumps(body),
                status=status,
                content_type="application/json",
            )

        request.make_json_response = make_json_response
        with (
            patch("odoo.addons.tms_telematics.controllers.webhook.request", request),
            self._patch_delay(bucket),
        ):
            queued = controller.hook(self.account.id)
            missing = controller.hook(999999)
            request.httprequest.data = b"not-json"
            invalid = controller.hook(self.account.id)
            request.httprequest.headers = {"X-Telematics-Token": "bad"}
            request.httprequest.data = b"{}"
            denied = controller.hook(self.account.id)
        self.assertEqual(queued.status_code, 200)
        self.assertEqual(json.loads(queued.get_data())["queued"], 0)
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(json.loads(missing.get_data())["error"], "unknown")
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(denied.status_code, 403)
