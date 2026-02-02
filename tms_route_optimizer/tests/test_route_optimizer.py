from datetime import datetime, timedelta

from odoo.exceptions import UserError
from odoo.tests import TransactionCase


class TestRouteOptimizer(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create team
        cls.team = cls.env["tms.team"].create(
            {
                "name": "Test Team",
            }
        )

        # Create vehicle type
        cls.vehicle_type = cls.env["fleet.vehicle.type"].create(
            {
                "name": "Test Van",
                "code": "TEST_VAN",
                "default_weight_capacity": 1500.0,
                "default_volume_capacity": 8.0,
                "default_cost_per_km": 2.50,
                "default_minimum_trip_cost": 50.0,
            }
        )

        # Create vehicle model (required field)
        cls.vehicle_model = cls.env["fleet.vehicle.model"].create(
            {
                "name": "Test Model",
                "brand_id": cls.env["fleet.vehicle.model.brand"].search([], limit=1).id
                or cls.env["fleet.vehicle.model.brand"]
                .create({"name": "Test Brand"})
                .id,
            }
        )

        # Create vehicle
        cls.vehicle = cls.env["fleet.vehicle"].create(
            {
                "name": "Test Vehicle",
                "model_id": cls.vehicle_model.id,
                "vehicle_type_id": cls.vehicle_type.id,
                "tms_team_id": cls.team.id,
                "weight_capacity": 1500.0,
                "volume_capacity": 8.0,
                "cost_per_km": 2.50,
                "minimum_trip_cost": 50.0,
            }
        )

        # Create depot
        cls.depot = cls.env["res.partner"].create(
            {
                "name": "Test Depot",
                "partner_latitude": -23.5505,
                "partner_longitude": -46.6333,
            }
        )

        cls.team.default_origin_location_id = cls.depot.id
        cls.team.default_destination_location_id = cls.depot.id

        # Create delivery partners
        cls.partner1 = cls.env["res.partner"].create(
            {
                "name": "Partner 1",
                "partner_latitude": -23.5500,
                "partner_longitude": -46.6300,
            }
        )

        cls.partner2 = cls.env["res.partner"].create(
            {
                "name": "Partner 2",
                "partner_latitude": -23.5510,
                "partner_longitude": -46.6340,
            }
        )

        # Create TMS order
        cls.order = cls.env["tms.order"].create(
            {
                "name": "Test Order",
                "tms_team_id": cls.team.id,
                "origin_id": cls.depot.id,
                "destination_id": cls.depot.id,
            }
        )

        # Create delivery stops
        now = datetime.now()
        cls.stop1 = cls.env["tms.order.stop"].create(
            {
                "order_id": cls.order.id,
                "partner_id": cls.partner1.id,
                "weight": 100.0,
                "volume": 1.0,
                "unloading_time": 30,
                "scheduled_date": now,
            }
        )

        cls.stop2 = cls.env["tms.order.stop"].create(
            {
                "order_id": cls.order.id,
                "partner_id": cls.partner2.id,
                "weight": 100.0,
                "volume": 1.0,
                "unloading_time": 30,
                "scheduled_date": now,
            }
        )

    def test_create_optimizer(self):
        """Test creating a route optimizer"""
        now = datetime.now()
        optimizer = self.env["tms.route.optimizer"].create(
            {
                "name": "Test Optimization",
                "team_id": self.team.id,
                "date_from": now - timedelta(hours=1),
                "date_to": now + timedelta(hours=1),
                "optimization_date": now.date(),
            }
        )

        self.assertEqual(optimizer.state, "draft")
        self.assertEqual(optimizer.team_id.id, self.team.id)

    def test_optimizer_auto_fill_stops(self):
        """Test that optimizer auto-fills delivery stops"""
        now = datetime.now()
        optimizer = self.env["tms.route.optimizer"].create(
            {
                "name": "Test Optimization",
                "team_id": self.team.id,
                "date_from": now - timedelta(hours=1),
                "date_to": now + timedelta(hours=1),
                "optimization_date": now.date(),
            }
        )

        # Trigger onchange
        optimizer._onchange_dates()

        # Should have auto-filled stops
        self.assertGreater(len(optimizer.delivery_stop_ids), 0)

    def test_optimizer_missing_geolocation(self):
        """Test that optimizer fails if stops have no geolocation"""
        # Create partner without geolocation
        partner_no_geo = self.env["res.partner"].create(
            {
                "name": "No Geo Partner",
            }
        )

        # Create order with stop without geolocation
        order = self.env["tms.order"].create(
            {
                "name": "Test Order No Geo",
                "tms_team_id": self.team.id,
            }
        )

        stop = self.env["tms.order.stop"].create(
            {
                "order_id": order.id,
                "partner_id": partner_no_geo.id,
                "weight": 100.0,
            }
        )

        now = datetime.now()
        optimizer = self.env["tms.route.optimizer"].create(
            {
                "name": "Test Optimization",
                "team_id": self.team.id,
                "date_from": now - timedelta(hours=1),
                "date_to": now + timedelta(hours=1),
                "optimization_date": now.date(),
                "delivery_stop_ids": [(6, 0, [stop.id])],
            }
        )

        # Should fail with geolocation error
        with self.assertRaises(UserError):
            optimizer.action_run_optimization()

    def test_optimizer_no_stops(self):
        """Test that optimizer fails if no stops provided"""
        now = datetime.now()
        optimizer = self.env["tms.route.optimizer"].create(
            {
                "name": "Test Optimization",
                "team_id": self.team.id,
                "date_from": now - timedelta(hours=1),
                "date_to": now + timedelta(hours=1),
                "optimization_date": now.date(),
            }
        )

        # Should fail with no stops error
        with self.assertRaises(UserError):
            optimizer.action_run_optimization()

    def test_optimizer_no_vehicles(self):
        """Test that optimizer fails if no vehicles in team"""
        # Create new team without vehicles
        team_no_vehicles = self.env["tms.team"].create(
            {
                "name": "Team No Vehicles",
            }
        )

        now = datetime.now()
        optimizer = self.env["tms.route.optimizer"].create(
            {
                "name": "Test Optimization",
                "team_id": team_no_vehicles.id,
                "date_from": now - timedelta(hours=1),
                "date_to": now + timedelta(hours=1),
                "optimization_date": now.date(),
                "delivery_stop_ids": [(6, 0, [self.stop1.id, self.stop2.id])],
            }
        )

        # Should fail with no vehicles error
        with self.assertRaises(UserError):
            optimizer.action_run_optimization()

    def test_optimizer_run_optimization(self):
        """Test running optimization"""
        now = datetime.now()
        optimizer = self.env["tms.route.optimizer"].create(
            {
                "name": "Test Optimization",
                "team_id": self.team.id,
                "date_from": now - timedelta(hours=1),
                "date_to": now + timedelta(hours=1),
                "optimization_date": now.date(),
                "delivery_stop_ids": [(6, 0, [self.stop1.id, self.stop2.id])],
            }
        )

        try:
            optimizer.action_run_optimization()

            # Check results
            self.assertEqual(optimizer.state, "done")
            self.assertGreater(optimizer.total_distance, 0)
            self.assertGreater(optimizer.total_cost, 0)
            self.assertGreater(optimizer.optimization_time, 0)
            self.assertGreater(len(optimizer.result_ids), 0)
        except Exception as e:
            # OR-Tools might not be installed in test environment
            if "ortools" not in str(e).lower():
                raise

    def test_optimizer_create_orders(self):
        """Test creating orders from optimization results"""
        now = datetime.now()
        optimizer = self.env["tms.route.optimizer"].create(
            {
                "name": "Test Optimization",
                "team_id": self.team.id,
                "date_from": now - timedelta(hours=1),
                "date_to": now + timedelta(hours=1),
                "optimization_date": now.date(),
                "delivery_stop_ids": [(6, 0, [self.stop1.id, self.stop2.id])],
            }
        )

        try:
            optimizer.action_run_optimization()

            # Create orders
            action = optimizer.action_create_orders()

            # Check action
            self.assertEqual(action["type"], "ir.actions.act_window")
            self.assertEqual(action["res_model"], "tms.order")

            # Check that stops are marked as scheduled
            self.stop1.invalidate_recordset()
            self.stop2.invalidate_recordset()
            self.assertEqual(self.stop1.state, "scheduled")
            self.assertEqual(self.stop2.state, "scheduled")
        except Exception as e:
            # OR-Tools might not be installed in test environment
            if "ortools" not in str(e).lower():
                raise
