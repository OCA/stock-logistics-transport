from datetime import datetime, timedelta

from odoo import _
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
                "mobile": "1234567890",
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
        order = self.create_order(name=_("New"))
        self.assertNotEqual(
            order.name, _("New"), "Name should be replaced by sequence code"
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
