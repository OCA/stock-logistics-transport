# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
from datetime import datetime, timedelta

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestTMSConvoy(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.origin = cls.env["res.partner"].create(
            {"name": "Convoy Origin", "tms_location": True}
        )
        cls.destination = cls.env["res.partner"].create(
            {"name": "Convoy Destination", "tms_location": True}
        )
        cls.yard = cls.env["res.partner"].create(
            {"name": "Convoy Yard", "tms_location": True}
        )
        brand = cls.env["fleet.vehicle.model.brand"].create({"name": "Convoy Brand"})
        model = cls.env["fleet.vehicle.model"].create(
            {"name": "Convoy Model", "brand_id": brand.id}
        )
        cls.tractor = cls.env["fleet.vehicle"].create(
            {
                "model_id": model.id,
                "license_plate": "TRC001",
                "tms_equipment_type": "power",
            }
        )
        cls.trailer = cls.env["fleet.vehicle"].create(
            {
                "model_id": model.id,
                "license_plate": "REM001",
                "tms_equipment_type": "trailer",
            }
        )
        cls.dolly = cls.env["fleet.vehicle"].create(
            {
                "model_id": model.id,
                "license_plate": "DOL001",
                "tms_equipment_type": "dolly",
            }
        )
        cls.driver = cls.env["tms.driver"].create(
            {"name": "Convoy Driver", "phone": "5550002"}
        )

    def _trip(self, **extra):
        values = {
            "origin_id": self.origin.id,
            "destination_id": self.destination.id,
            "vehicle_id": self.tractor.id,
            "driver_id": self.driver.id,
        }
        values.update(extra)
        return self.env["tms.order"].create(values)

    def test_convoy_role_follows_the_vehicle(self):
        trip = self._trip()
        trailer = self.env["tms.order.equipment"].create(
            {"order_id": trip.id, "vehicle_id": self.trailer.id}
        )
        dolly = self.env["tms.order.equipment"].create(
            {"order_id": trip.id, "vehicle_id": self.dolly.id}
        )
        self.assertEqual(trailer.role, "trailer")
        self.assertEqual(dolly.role, "dolly")

    def test_power_unit_cannot_join_the_convoy(self):
        trip = self._trip()
        with self.assertRaises(ValidationError):
            self.env["tms.order.equipment"].create(
                {"order_id": trip.id, "vehicle_id": self.tractor.id}
            )

    def test_drop_moves_the_trailer_location(self):
        trip = self._trip()
        line = self.env["tms.order.equipment"].create(
            {"order_id": trip.id, "vehicle_id": self.trailer.id}
        )
        line.action_drop()
        self.assertTrue(line.dropped)
        self.assertEqual(line.drop_location_id, self.destination)
        self.assertEqual(self.trailer.tms_location_id, self.destination)
        self.assertTrue(line.drop_date)
        line.action_drop()
        self.assertTrue(line.dropped)

    def test_drop_uses_the_chosen_location(self):
        trip = self._trip()
        line = self.env["tms.order.equipment"].create(
            {
                "order_id": trip.id,
                "vehicle_id": self.trailer.id,
                "drop_location_id": self.yard.id,
            }
        )
        line.action_drop()
        self.assertEqual(line.drop_location_id, self.yard)
        self.assertEqual(self.trailer.tms_location_id, self.yard)

    def test_dolly_cannot_be_dropped(self):
        trip = self._trip()
        line = self.env["tms.order.equipment"].create(
            {"order_id": trip.id, "vehicle_id": self.dolly.id}
        )
        with self.assertRaises(UserError):
            line.action_drop()
        self.assertFalse(line.dropped)

    def test_odometer_split_must_match_the_difference(self):
        trip = self._trip()
        with self.assertRaises(ValidationError):
            trip.write(
                {
                    "odometer_start": 1000,
                    "odometer_end": 1200,
                    "distance_loaded": 100,
                    "distance_empty": 50,
                }
            )
        with self.assertRaises(ValidationError):
            trip.write({"odometer_start": 1500, "odometer_end": 1200})
        trip.write(
            {
                "odometer_start": 1000,
                "odometer_end": 1200,
                "distance_loaded": 150,
                "distance_empty": 50,
            }
        )
        self.assertEqual(trip.distance_loaded, 150)
        self.assertEqual(trip.distance_empty, 50)

    def test_odometer_readings_alone_are_accepted(self):
        trip = self._trip()
        trip.write({"odometer_start": 1000, "odometer_end": 1100})
        self.assertEqual(trip.distance_loaded, 0)
        self.assertEqual(trip.distance_empty, 0)

    def test_proof_of_delivery_does_not_block_completed(self):
        trip = self._trip()
        attachment = self.env["ir.attachment"].create(
            {
                "name": "pod.txt",
                "datas": base64.b64encode(b"signed"),
            }
        )
        completed = self.env.ref("tms.tms_stage_order_completed")
        trip.write(
            {
                "pod_note": "Received by the warehouse",
                "pod_attachment_ids": [(4, attachment.id)],
                "stage_id": completed.id,
            }
        )
        self.assertEqual(trip.pod_note, "Received by the warehouse")
        self.assertEqual(trip.pod_attachment_ids, attachment)
        self.assertTrue(trip.stage_id.is_completed)

    def test_trip_without_a_driver_still_starts(self):
        trip = self._trip(driver_id=False)
        trip.button_start_order()
        self.assertTrue(trip.start_trip)
        trip.button_end_order()
        self.assertTrue(trip.end_trip)
        self.assertFalse(trip.start_trip)

    def test_driver_stage_follows_the_trip(self):
        in_trip = self.env.ref("tms.tms_stage_driver_in_trip")
        in_base = self.env.ref("tms.tms_stage_driver_in_base")
        first = self._trip()
        second = self._trip()
        first.button_start_order()
        self.assertEqual(self.driver.stage_id, in_trip)
        with self.assertRaises(UserError):
            second.button_start_order()
        first.date_end = datetime.now() + timedelta(hours=1)
        first.button_end_order()
        self.assertEqual(self.driver.stage_id, in_base)
        second.button_start_order()
        self.assertEqual(self.driver.stage_id, in_trip)

    def test_driver_stays_out_while_another_trip_is_running(self):
        in_trip = self.env.ref("tms.tms_stage_driver_in_trip")
        first = self._trip()
        second = self._trip()
        first.button_start_order()
        second.write({"start_trip": True, "date_start": datetime.now()})
        first.button_end_order()
        self.assertEqual(self.driver.stage_id, in_trip)
        self.assertTrue(second.start_trip)
