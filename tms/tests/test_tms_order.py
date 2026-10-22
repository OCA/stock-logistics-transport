from datetime import datetime, timedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestTMSOrder(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.origin_location = (
            cls.env["res.partner"]
            .create(
                {
                    "name": "Test Origin Location",
                    "tms_location": True,
                }
            )
            .id
        )

        cls.destination_location = (
            cls.env["res.partner"]
            .create(
                {
                    "name": "Test Destination Location",
                    "tms_location": True,
                }
            )
            .id
        )

        cls.driver = cls.env["tms.driver"].create(
            {
                "name": "Test Driver",
                "phone": "1234567890",
            }
        )

        cls.vehicle = cls.env["fleet.vehicle"].create(
            {
                "name": "Test Vehicle",
                "license_plate": "ABC123",
                "model_id": cls.env["fleet.vehicle.model"]
                .create(
                    {
                        "name": "Test Model",
                        "brand_id": cls.env["fleet.vehicle.model.brand"]
                        .create({"name": "Test Brand"})
                        .id,
                    }
                )
                .id,
            }
        )

        cls.location = cls.env["res.partner"].create(
            {
                "name": "Test Location",
                "tms_location": True,
            }
        )

        cls.route = cls.env["tms.route"].create(
            {
                "name": "Test Route",
                "estimated_time": 2.0,
                "estimated_time_uom": cls.env.ref("uom.product_uom_hour").id,
                "origin_location_id": cls.origin_location,
                "destination_location_id": cls.destination_location,
            }
        )

        cls.crew = cls.env["tms.crew"].create(
            {
                "name": "Test Crew",
                "driver_ids": [(6, 0, [cls.driver.id])],
                "default_vehicle_id": cls.vehicle.id,
            }
        )

        cls.team = cls.env["tms.team"].create(
            {
                "name": "Test Team Trip",
                "driver_ids": [(6, 0, [cls.driver.id])],
                "vehicle_ids": [(6, 0, [cls.vehicle.id])],
            }
        )

    def create_order(self, **kwargs):
        return self.env["tms.order"].create(
            {
                "name": "Test Order",
                "company_id": self.env.company.id,
                "origin_id": self.origin_location,
                "destination_id": self.destination_location,
                **kwargs,
            }
        )

    def test_calculate_scheduled_duration(self):
        start_time = datetime.now()
        order = self.create_order(
            scheduled_date_start=start_time, scheduled_duration=2.0
        )
        order._compute_scheduled_date_end()
        expected_end_time = start_time + timedelta(hours=2.0)
        self.assertEqual(
            order.scheduled_date_end,
            expected_end_time,
            "Scheduled end date calculation is incorrect",
        )

        order.scheduled_date_end = datetime.now() + timedelta(hours=3.0)
        order._compute_scheduled_duration()
        expected_duration = (
            order.scheduled_date_end - order.scheduled_date_start
        ).total_seconds() / 3600
        self.assertEqual(
            order.scheduled_duration,
            expected_duration,
            "Scheduled duration calculation is incorrect",
        )

    def test_button_start_order(self):
        order = self.create_order(scheduled_date_start=datetime.now())
        order.button_start_order()
        self.assertTrue(
            order.start_trip, "Start trip flag should be True after starting the order"
        )
        self.assertEqual(order.stage_id, self.env.ref("tms.tms_stage_order_in_transit"))

        order.button_refresh_duration()
        refresh_duration = (order.date_end - order.date_start).total_seconds() / 3600
        self.assertEqual(
            order.duration, refresh_duration, "Refresh duration is incorrect"
        )

    def test_button_end_order(self):
        order = self.create_order(
            scheduled_date_start=datetime.now(), scheduled_duration=1.0
        )
        order.button_start_order()
        order.date_start = datetime.now()
        order.date_end = order.date_start + timedelta(hours=1)
        order.button_end_order()
        self.assertTrue(
            order.end_trip, "End trip flag should be True after ending the order"
        )
        self.assertFalse(
            order.start_trip, "Start trip flag should be False after ending the order"
        )
        self.assertEqual(order.stage_id, self.env.ref("tms.tms_stage_order_arrived"))

        diff_duration = round(order.scheduled_duration - order.duration, 2)
        self.assertEqual(
            order.diff_duration,
            diff_duration,
            "Difference between scheduled duration and actual duration is incorrect",
        )

    def test_default_time_uom(self):
        uom = self.env.ref("uom.product_uom_hour")
        order = self.create_order()
        self.assertEqual(order.time_uom, uom, "Default UOM should be hours")

    def test_stage_and_cargo_state_are_logged(self):
        order = self.create_order()
        self.env.cr.flush()
        arrived = self.env.ref("tms.tms_stage_order_arrived")
        order.stage_id = arrived
        self.env.cr.flush()
        stage_track = order.message_ids.tracking_value_ids.filtered(
            lambda value: value.field_id.name == "stage_id"
        )
        self.assertTrue(stage_track)
        cargo = self.env["tms.cargo"].create(
            {"name": "Logged box", "order_id": order.id}
        )
        self.env.cr.flush()
        cargo.state = "loaded"
        self.env.cr.flush()
        state_track = cargo.message_ids.tracking_value_ids.filtered(
            lambda value: value.field_id.name == "state"
        )
        self.assertTrue(state_track)

    def test_default_stage_id(self):
        stage = self.env["tms.stage"].create(
            {
                "name": "Default Stage",
                "stage_type": "order",
                "sequence": 1,
            }
        )
        order = self.create_order()
        self.assertEqual(
            order.stage_id, stage, "Default stage should be assigned correctly"
        )

    def test_create_with_sequence(self):
        self.env["ir.sequence"].create(
            {
                "name": "TMS Order Sequence",
                "code": "tms.order",
                "prefix": "TMS/",
                "padding": 5,
            }
        )
        new_name = self.env._("New")
        order = self.create_order(name=new_name)
        self.assertNotEqual(
            order.name, new_name, "Name should be replaced by sequence code"
        )
        self.assertTrue(
            order.name.startswith("TMS/"), "Name should start with sequence prefix"
        )

    def test_order_with_crew(self):
        order = self.create_order(crew_id=self.crew.id)
        order._compute_active_crew()
        self.assertEqual(
            order.crew_id, self.crew, "Crew wasn't assigned successfully to order"
        )
        self.assertEqual(
            order.vehicle_id,
            self.crew.default_vehicle_id,
            "Default vehicle from crew should appear in order",
        )

    def test_order_with_team(self):
        order = self.create_order(tms_team_id=self.team.id)
        order._compute_active_crew()
        self.assertEqual(
            order.tms_team_id, self.team, "Team wasn't assigned successfully to order"
        )

    def test_distance_uses_the_route_length(self):
        kilometer = self.env.ref("uom.product_uom_km")
        self.route.distance = 100.0
        self.route.distance_uom = kilometer
        order = self.create_order(route=True, route_id=self.route.id)
        self.assertAlmostEqual(order.distance, 100.0)
        self.assertEqual(order.distance_uom_id, kilometer)

    def test_manual_distance_stays_without_a_provider(self):
        kilometer = self.env.ref("uom.product_uom_km")
        order = self.create_order(distance=42.0, distance_uom_id=kilometer.id)
        self.assertTrue(order.distance_editable)
        self.assertAlmostEqual(order.distance, 42.0)
        self.assertEqual(order.distance_uom_id, kilometer)
        origin = self.env["res.partner"].browse(self.origin_location)
        destination = self.env["res.partner"].browse(self.destination_location)
        origin.write({"partner_latitude": 29.76, "partner_longitude": -95.36})
        destination.write({"partner_latitude": 32.77, "partner_longitude": -96.79})
        self.assertAlmostEqual(order.distance, 42.0)
        self.assertEqual(order.distance_uom_id, kilometer)

    def test_distance_without_coordinates_stays_empty(self):
        order = self.create_order()
        self.assertEqual(order.distance, 0.0)
        self.assertTrue(order.distance_editable)

    def _window(self, order, start, hours, **extra):
        values = {
            "scheduled_date_start": fields.Datetime.to_datetime(start),
            "scheduled_duration": hours,
        }
        values.update(extra)
        order.write(values)
        return order

    def test_overlapping_vehicle_and_driver_are_refused(self):
        first = self._window(
            self.create_order(name="Overlap A", vehicle_id=self.vehicle.id),
            "2026-10-10 08:00:00",
            6.0,
            driver_id=self.driver.id,
        )
        second = self.create_order(name="Overlap B")
        with self.assertRaises(ValidationError):
            self._window(
                second,
                "2026-10-10 10:00:00",
                4.0,
                vehicle_id=self.vehicle.id,
            )
        other_vehicle = self.env["fleet.vehicle"].create(
            {
                "name": "Other Vehicle",
                "license_plate": "XYZ789",
                "model_id": self.vehicle.model_id.id,
            }
        )
        self._window(
            second,
            "2026-10-10 10:00:00",
            4.0,
            vehicle_id=other_vehicle.id,
        )
        with self.assertRaises(ValidationError):
            second.driver_id = self.driver
        self.assertEqual(first.driver_id, self.driver)

    def test_a_later_trip_can_reuse_the_vehicle_and_driver(self):
        self._window(
            self.create_order(
                name="Morning",
                vehicle_id=self.vehicle.id,
                driver_id=self.driver.id,
            ),
            "2026-10-10 08:00:00",
            4.0,
        )
        later = self._window(
            self.create_order(
                name="Afternoon",
                vehicle_id=self.vehicle.id,
                driver_id=self.driver.id,
            ),
            "2026-10-10 12:00:00",
            4.0,
        )
        self.assertEqual(later.vehicle_id, self.vehicle)
        self.assertEqual(later.driver_id, self.driver)

    def test_a_done_trip_releases_the_vehicle(self):
        first = self._window(
            self.create_order(name="Done", vehicle_id=self.vehicle.id),
            "2026-10-10 08:00:00",
            8.0,
        )
        first.end_trip = True
        second = self._window(
            self.create_order(name="Next", vehicle_id=self.vehicle.id),
            "2026-10-10 10:00:00",
            4.0,
        )
        self.assertEqual(second.vehicle_id, self.vehicle)

    def test_origin_and_destination_are_partners(self):
        order_fields = self.env["tms.order"]._fields
        for name in (
            "origin_id",
            "destination_id",
            "origin_location",
            "destination_location",
            "route_origin",
            "route_destination",
        ):
            field = order_fields[name]
            self.assertEqual(field.type, "many2one")
            self.assertEqual(field.comodel_name, "res.partner")
        route_fields = self.env["tms.route"]._fields
        for name in ("origin_location_id", "destination_location_id"):
            field = route_fields[name]
            self.assertEqual(field.type, "many2one")
            self.assertEqual(field.comodel_name, "res.partner")
