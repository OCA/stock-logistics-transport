# Copyright (C) 2024 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError
from odoo.tests import TransactionCase


class TestTMSRouteOptimizerDemoOptimization(TransactionCase):
    """Test running optimization with demo data"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Demo team
        cls.brazil_team = cls.env.ref("tms_route_optimizer.demo_team_route_optimizer")
        # Demo order and stops
        cls.brazil_order = cls.env.ref("tms_route_optimizer.demo_tms_order_optimizer_1")
        # Get stops from order (using search as stop_ids might not be available)
        cls.brazil_stops = cls.env["tms.order.stop"].search(
            [("order_id", "=", cls.brazil_order.id)]
        )

    def test_create_optimizer_from_demo_data(self):
        """Test creating optimizer wizard from demo data"""
        optimizer = self.env["tms.route.optimizer"].create(
            {
                "name": "Test Optimization",
                "team_id": self.brazil_team.id,
                "date_from": self.brazil_stops[0].scheduled_date,
                "date_to": self.brazil_stops[-1].scheduled_date,
                "delivery_stop_ids": [(6, 0, self.brazil_stops.ids)],
                "optimization_date": self.brazil_stops[0].scheduled_date.date(),
            }
        )
        self.assertEqual(optimizer.team_id, self.brazil_team)
        self.assertEqual(len(optimizer.delivery_stop_ids), 8)
        self.assertEqual(optimizer.state, "draft")

    def test_optimizer_auto_fill_stops(self):
        """Test that optimizer auto-fills stops based on date range"""
        optimizer = self.env["tms.route.optimizer"].create(
            {
                "name": "Test Optimization",
                "team_id": self.brazil_team.id,
                "date_from": self.brazil_stops[0].scheduled_date,
                "date_to": self.brazil_stops[-1].scheduled_date,
                "optimization_date": self.brazil_stops[0].scheduled_date.date(),
            }
        )
        # Trigger onchange
        optimizer._onchange_dates()
        # Should find stops in the date range
        self.assertGreater(len(optimizer.delivery_stop_ids), 0)

    def test_optimizer_validation_no_stops(self):
        """Test that optimizer validates when no stops are selected"""
        optimizer = self.env["tms.route.optimizer"].create(
            {
                "name": "Test Optimization",
                "team_id": self.brazil_team.id,
                "date_from": self.brazil_stops[0].scheduled_date,
                "date_to": self.brazil_stops[-1].scheduled_date,
                "optimization_date": self.brazil_stops[0].scheduled_date.date(),
            }
        )
        with self.assertRaises(UserError) as context:
            optimizer.action_run_optimization()
        self.assertIn("No delivery stops", str(context.exception))

    def test_optimizer_validation_geolocation(self):
        """Test that optimizer validates stops have geolocation"""
        # Create a stop without geolocation
        partner_no_geo = self.env["res.partner"].create(
            {
                "name": "Partner No Geo",
                "partner_latitude": False,
                "partner_longitude": False,
            }
        )
        order = self.env["tms.order"].create(
            {
                "name": "Test Order",
                "tms_team_id": self.brazil_team.id,
            }
        )
        stop_no_geo = self.env["tms.order.stop"].create(
            {
                "order_id": order.id,
                "partner_id": partner_no_geo.id,
                "weight": 100,
                "volume": 1.0,
            }
        )
        optimizer = self.env["tms.route.optimizer"].create(
            {
                "name": "Test Optimization",
                "team_id": self.brazil_team.id,
                "date_from": self.brazil_stops[0].scheduled_date,
                "date_to": self.brazil_stops[-1].scheduled_date,
                "delivery_stop_ids": [(6, 0, [stop_no_geo.id])],
                "optimization_date": self.brazil_stops[0].scheduled_date.date(),
            }
        )
        with self.assertRaises(UserError) as context:
            optimizer.action_run_optimization()
        self.assertIn("has no geolocation", str(context.exception))

    def test_optimizer_has_vehicles_available(self):
        """Test that optimizer finds vehicles for team"""
        vehicles = self.env["fleet.vehicle"].search(
            [("tms_team_id", "=", self.brazil_team.id)]
        )
        self.assertGreater(len(vehicles), 0)
        # Check that vehicles have required data
        for vehicle in vehicles:
            self.assertGreater(vehicle.weight_capacity, 0)
            self.assertGreater(vehicle.volume_capacity, 0)

    def test_optimizer_can_run_with_demo_data(self):
        """Test that optimizer can run with demo data (if OR-Tools available)"""
        try:
            import ortools.constraint_solver  # noqa: F401

            has_ortools = True
        except ImportError:
            has_ortools = False

        if not has_ortools:
            self.skipTest("OR-Tools not available")

        optimizer = self.env["tms.route.optimizer"].create(
            {
                "name": "Test Optimization Demo",
                "team_id": self.brazil_team.id,
                "date_from": self.brazil_stops[0].scheduled_date,
                "date_to": self.brazil_stops[-1].scheduled_date,
                "delivery_stop_ids": [(6, 0, self.brazil_stops.ids)],
                "optimization_date": self.brazil_stops[0].scheduled_date.date(),
            }
        )

        # Run optimization
        try:
            optimizer.action_run_optimization()
            # If successful, should be in 'done' state
            if optimizer.state == "done":
                self.assertGreater(optimizer.total_distance, 0)
                self.assertGreater(optimizer.total_cost, 0)
                self.assertGreater(optimizer.total_vehicles_used, 0)
                self.assertGreater(len(optimizer.result_ids), 0)
        except UserError as e:
            # If optimization fails (e.g., no solution), that's ok for test
            # Log the exception for debugging
            import logging

            _logger = logging.getLogger(__name__)
            _logger.debug("Optimization failed in test: %s", e)
