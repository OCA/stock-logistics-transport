from datetime import datetime, timedelta

from odoo import _
from odoo.tests.common import TransactionCase


class TestTMSOrder(TransactionCase):
    def setUp(self):
        super().setUp()

        self.origin_location = (
            self.env["res.partner"]
            .create(
                {
                    "name": "Test Origin Location",
                    "tms_type": "location",
                }
            )
            .id
        )

        self.destination_location = (
            self.env["res.partner"]
            .create(
                {
                    "name": "Test Destination Location",
                    "tms_type": "location",
                }
            )
            .id
        )

    def create_trip(self):
        trip = self.env["tms.order"].create(
            {
                "name": "Test Trip Manager",
                "driver_id": self.driver.id,
                "vehicle_id": self.vehicle.id,
                "origin_id": self.location.id,
                "destination_id": self.location.id,
            }
        )
        self.assertTrue(trip, "Trip wasn't created successfully")
        self.assertEqual(
            trip.driver_id, trip.driver, "Driver wasn't created successfully"
        )
        self.assertEqual(
            trip.vehicle_id, trip.vehicle, "Vehicle wasn't created successfully"
        )
        self.assertEqual(
            trip.origin_id,
            trip.origin_location,
            "Origin location should be correctly assigned",
        )
        self.assertEqual(
            trip.destination_id,
            trip.destination_location,
            "Destination location wasn't created successfully",
        )

    def test_onchange_route(self):
        order = self.env["tms.order"].create(
            {
                "name": "Test Order",
                "company_id": self.env.company.id,
            }
        )
        order.route = False
        order._onchange_route()
        self.assertFalse(order.route_id, "route_id should be None when route is False")
        order.route = True
        order._onchange_route()

        self.assertFalse(order.origin_id, "Origin should be False when route is False")
        self.assertFalse(
            order.destination_id, "Destination should be False when route is False"
        )

        uom_hour = self.env.ref("uom.product_uom_hour").id
        uom_day = self.env.ref("uom.product_uom_day").id

        route = self.env["tms.route"].create(
            {
                "name": "Test Route",
                "estimated_time": 2.0,
                "estimated_time_uom": uom_hour,
                "origin_location_id": self.origin_location,
                "destination_location_id": self.destination_location,
            }
        )

        order.route_id = route
        order._onchange_route_id()
        self.assertEqual(
            order.scheduled_duration,
            route.estimated_time,
            "Route and order scheduled duration should be equal",
        )

        route.estimated_time_uom = uom_day
        order._onchange_route_id()
        self.assertEqual(
            order.scheduled_duration,
            route.estimated_time * 24,
            "Order scheduled duration should be equal to the days in hours",
        )

    def test_calculate_scheduled_duration(self):
        start_time = datetime.now()
        order = self.env["tms.order"].create(
            {
                "name": "Test Order",
                "company_id": self.env.company.id,
                "scheduled_date_start": start_time,
                "scheduled_duration": 2.0,
            }
        )
        order._onchange_scheduled_duration()
        date_end = order.scheduled_date_start + timedelta(
            hours=order.scheduled_duration
        )
        self.assertEqual(
            order.scheduled_date_end, date_end, "date_end calculation is incorrect"
        )

        order.scheduled_date_end = datetime.now() + timedelta(hours=3.0)
        order._onchange_scheduled_date_end()
        duration = (
            order.scheduled_date_end - order.scheduled_date_start
        ).total_seconds() / 3600
        self.assertEqual(
            order.scheduled_duration,
            duration,
            "scheduled_duration calculation is incorrect",
        )

    def test_button_start_order(self):
        order = self.env["tms.order"].create(
            {
                "name": "Test Order",
                "company_id": self.env.company.id,
                "scheduled_date_start": datetime.now(),
            }
        )
        order.button_start_order()
        self.assertTrue(
            order.start_trip, "Start trip flag should be True after starting the order"
        )

        order.button_refresh_duration()
        refresh_duration = (order.date_end - order.date_start).total_seconds() / 3600
        self.assertEqual(
            order.duration, refresh_duration, "refresh duration is incorrect"
        )

    def test_button_end_order(self):
        order = self.env["tms.order"].create(
            {
                "name": "Test Order",
                "company_id": self.env.company.id,
                "scheduled_date_start": datetime.now(),
                "scheduled_duration": 1.0,
            }
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
            "Difference between scheduled duration and duration is incorrect",
        )

    def test_default_time_uom(self):
        uom = self.env.ref("uom.product_uom_hour")
        order = self.env["tms.order"].create(
            {
                "name": "Test Order",
                "company_id": self.env.company.id,
            }
        )
        self.assertEqual(order.time_uom, uom, "Default UOM should be hours")

    def test_default_stage_id(self):
        stage = self.env["tms.stage"].create(
            {
                "name": "Default Stage",
                "stage_type": "order",
                "sequence": 1,
            }
        )
        order = self.env["tms.order"].create(
            {
                "name": "Test Order",
                "company_id": self.env.company.id,
            }
        )
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
        order = self.env["tms.order"].create(
            {
                "name": _("New"),
                "company_id": self.env.company.id,
            }
        )
        self.assertNotEqual(
            order.name, _("New"), "Name should be replaced by sequence code"
        )
        self.assertTrue(
            order.name.startswith("TMS/"), "Name should start with sequence prefix"
        )

    def test_order_with_crew(self):
        driver = self.env["res.partner"].create(
            {
                "name": "Test Driver",
                "tms_type": "driver",
                "mobile": "1234567890",
            }
        )

        vehicle = (
            self.env["fleet.vehicle"]
            .create(
                {
                    "name": "Test Vehicle",
                    "license_plate": "ABC123",
                    "model_id": self.env["fleet.vehicle.model"]
                    .create(
                        {
                            "name": "Test Model",
                            "brand_id": self.env["fleet.vehicle.model.brand"]
                            .create({"name": "Test Brand"})
                            .id,
                        }
                    )
                    .id,
                }
            )
            .id
        )

        crew = self.env["tms.crew"].create(
            {
                "name": "Test Crew",
                "driver_ids": driver,
                "default_vehicle_id": vehicle,
            }
        )
        order = self.env["tms.order"].create(
            {"name": _("New"), "company_id": self.env.company.id, "crew_id": crew.id}
        )
        order._compute_active_crew()
        self.assertEqual(
            order.crew_id, crew, "Crew wasn't assigned successfully to order"
        )
        self.assertEqual(
            order.vehicle_id,
            crew.default_vehicle_id,
            "Default vehicle from crew should appear in order",
        )

    def test_order_with_team(self):
        driver = self.env["res.partner"].create(
            {
                "name": "Test Driver",
                "tms_type": "driver",
                "mobile": "1234567890",
            }
        )

        vehicle = (
            self.env["fleet.vehicle"]
            .create(
                {
                    "name": "Test Vehicle",
                    "license_plate": "ABC123",
                    "model_id": self.env["fleet.vehicle.model"]
                    .create(
                        {
                            "name": "Test Model",
                            "brand_id": self.env["fleet.vehicle.model.brand"]
                            .create({"name": "Test Brand"})
                            .id,
                        }
                    )
                    .id,
                }
            )
            .id
        )

        team = self.env["tms.team"].create(
            {
                "name": "Test Team Trip",
                "driver_ids": driver,
                "vehicle_ids": [(6, 0, [vehicle])],
            }
        )

        order = self.env["tms.order"].create(
            {
                "name": _("New"),
                "company_id": self.env.company.id,
                "tms_team_id": team.id,
            }
        )
        order._compute_active_crew()
        self.assertEqual(
            order.tms_team_id, team, "Team wasn't assigned successfully to order"
        )
