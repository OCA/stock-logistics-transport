"""Tests for automatic optimization configuration and suggestions."""

from datetime import datetime

from odoo.exceptions import UserError
from odoo.tests import TransactionCase


class TestOptimizerConfig(TransactionCase):
    """Test the automatic optimization configuration model."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create team
        cls.team = cls.env["tms.team"].create({"name": "Test Team"})

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

        # Create vehicle model
        brand = cls.env["fleet.vehicle.model.brand"].create({"name": "Test Brand"})
        cls.vehicle_model = cls.env["fleet.vehicle.model"].create(
            {
                "name": "Test Model",
                "brand_id": brand.id,
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

    def test_create_config(self):
        """Test creating an optimization configuration."""
        config = self.env["tms.route.optimizer.config"].create(
            {
                "name": "Test Config",
                "team_id": self.team.id,
                "planning_mode": "team",
            }
        )

        self.assertEqual(config.name, "Test Config")
        self.assertEqual(config.team_id, self.team)
        self.assertEqual(config.planning_mode, "team")
        self.assertTrue(config.active)

    def test_config_default_values(self):
        """Test default values for configuration."""
        config = self.env["tms.route.optimizer.config"].create(
            {
                "name": "Test Config",
                "team_id": self.team.id,
            }
        )

        self.assertEqual(config.planning_mode, "team")
        self.assertEqual(config.vehicles_per_type, 5)
        self.assertEqual(config.max_stops_per_vehicle, 0)
        self.assertTrue(config.enable_multi_day)
        self.assertEqual(config.planning_horizon_days, 3)
        self.assertEqual(config.cron_hour, 22)
        self.assertEqual(config.cron_minute, 0)
        self.assertEqual(config.days_ahead, 3)

    def test_config_cron_hour_constraint(self):
        """Test that cron hour must be valid."""
        with self.assertRaises(UserError):
            self.env["tms.route.optimizer.config"].create(
                {
                    "name": "Test Config",
                    "team_id": self.team.id,
                    "cron_hour": 25,  # Invalid
                }
            )

    def test_config_cron_minute_constraint(self):
        """Test that cron minute must be valid."""
        with self.assertRaises(UserError):
            self.env["tms.route.optimizer.config"].create(
                {
                    "name": "Test Config",
                    "team_id": self.team.id,
                    "cron_minute": 60,  # Invalid
                }
            )

    def test_config_with_vehicles(self):
        """Test configuration with specific vehicles."""
        config = self.env["tms.route.optimizer.config"].create(
            {
                "name": "Test Config",
                "team_id": self.team.id,
                "planning_mode": "vehicles",
                "vehicle_ids": [(6, 0, [self.vehicle.id])],
            }
        )

        self.assertEqual(config.planning_mode, "vehicles")
        self.assertIn(self.vehicle, config.vehicle_ids)

    def test_config_with_vehicle_types(self):
        """Test configuration with vehicle types."""
        config = self.env["tms.route.optimizer.config"].create(
            {
                "name": "Test Config",
                "team_id": self.team.id,
                "planning_mode": "vehicle_types",
                "vehicle_type_ids": [(6, 0, [self.vehicle_type.id])],
                "vehicles_per_type": 3,
            }
        )

        self.assertEqual(config.planning_mode, "vehicle_types")
        self.assertIn(self.vehicle_type, config.vehicle_type_ids)
        self.assertEqual(config.vehicles_per_type, 3)

    def test_config_suggestion_count(self):
        """Test computed suggestion count."""
        config = self.env["tms.route.optimizer.config"].create(
            {
                "name": "Test Config",
                "team_id": self.team.id,
            }
        )

        self.assertEqual(config.suggestion_count, 0)
        self.assertEqual(config.pending_suggestion_count, 0)

        # Create a suggestion
        self.env["tms.route.suggestion"].create(
            {
                "name": "Test Suggestion",
                "config_id": config.id,
                "planning_date": datetime.now().date(),
                "state": "suggested",
            }
        )

        config.invalidate_recordset()

        self.assertEqual(config.suggestion_count, 1)
        self.assertEqual(config.pending_suggestion_count, 1)

    def test_expire_old_suggestions(self):
        """Test expiring old suggestions."""
        config = self.env["tms.route.optimizer.config"].create(
            {
                "name": "Test Config",
                "team_id": self.team.id,
            }
        )

        # Create a suggestion
        suggestion = self.env["tms.route.suggestion"].create(
            {
                "name": "Test Suggestion",
                "config_id": config.id,
                "planning_date": datetime.now().date(),
                "state": "suggested",
            }
        )

        config._expire_old_suggestions()

        suggestion.invalidate_recordset()
        self.assertEqual(suggestion.state, "expired")

    def test_get_eligible_stops_empty(self):
        """Test getting eligible stops when none exist."""
        config = self.env["tms.route.optimizer.config"].create(
            {
                "name": "Test Config",
                "team_id": self.team.id,
            }
        )

        stops = config._get_eligible_stops()

        # Should be empty (no draft stops in system)
        self.assertEqual(len(stops), 0)


class TestRouteSuggestion(TransactionCase):
    """Test the route suggestion model."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create team
        cls.team = cls.env["tms.team"].create({"name": "Test Team"})

        # Create vehicle type
        cls.vehicle_type = cls.env["fleet.vehicle.type"].create(
            {
                "name": "Test Van",
                "code": "TEST_VAN",
                "default_weight_capacity": 1500.0,
                "default_volume_capacity": 8.0,
            }
        )

        # Create vehicle model
        brand = cls.env["fleet.vehicle.model.brand"].create({"name": "Test Brand"})
        cls.vehicle_model = cls.env["fleet.vehicle.model"].create(
            {
                "name": "Test Model",
                "brand_id": brand.id,
            }
        )

        # Create vehicle
        cls.vehicle = cls.env["fleet.vehicle"].create(
            {
                "name": "Test Vehicle",
                "model_id": cls.vehicle_model.id,
                "vehicle_type_id": cls.vehicle_type.id,
                "tms_team_id": cls.team.id,
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

        # Create config
        cls.config = cls.env["tms.route.optimizer.config"].create(
            {
                "name": "Test Config",
                "team_id": cls.team.id,
            }
        )

        # Create partners
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

        # Create order and stops
        cls.order = cls.env["tms.order"].create(
            {
                "name": "Test Order",
                "tms_team_id": cls.team.id,
            }
        )

        now = datetime.now()
        cls.stop1 = cls.env["tms.order.stop"].create(
            {
                "order_id": cls.order.id,
                "partner_id": cls.partner1.id,
                "weight": 100.0,
                "scheduled_date": now,
            }
        )

        cls.stop2 = cls.env["tms.order.stop"].create(
            {
                "order_id": cls.order.id,
                "partner_id": cls.partner2.id,
                "weight": 100.0,
                "scheduled_date": now,
            }
        )

    def test_create_suggestion(self):
        """Test creating a route suggestion."""
        suggestion = self.env["tms.route.suggestion"].create(
            {
                "name": "Test Suggestion",
                "config_id": self.config.id,
                "planning_date": datetime.now().date(),
                "vehicle_id": self.vehicle.id,
                "stop_ids": [(6, 0, [self.stop1.id, self.stop2.id])],
            }
        )

        self.assertEqual(suggestion.state, "suggested")
        self.assertEqual(suggestion.team_id, self.team)
        self.assertEqual(suggestion.stop_count, 2)

    def test_suggestion_reject(self):
        """Test rejecting a suggestion."""
        suggestion = self.env["tms.route.suggestion"].create(
            {
                "name": "Test Suggestion",
                "config_id": self.config.id,
                "planning_date": datetime.now().date(),
                "vehicle_id": self.vehicle.id,
            }
        )

        suggestion.action_reject()

        self.assertEqual(suggestion.state, "rejected")

    def test_suggestion_reject_non_suggested_raises(self):
        """Test that rejecting non-suggested raises error."""
        suggestion = self.env["tms.route.suggestion"].create(
            {
                "name": "Test Suggestion",
                "config_id": self.config.id,
                "planning_date": datetime.now().date(),
                "vehicle_id": self.vehicle.id,
                "state": "approved",
            }
        )

        with self.assertRaises(UserError):
            suggestion.action_reject()

    def test_suggestion_approve_creates_order(self):
        """Test that approving a suggestion creates an order."""
        suggestion = self.env["tms.route.suggestion"].create(
            {
                "name": "Test Suggestion",
                "config_id": self.config.id,
                "planning_date": datetime.now().date(),
                "vehicle_id": self.vehicle.id,
                "stop_ids": [(6, 0, [self.stop1.id, self.stop2.id])],
            }
        )

        result = suggestion.action_approve()

        self.assertEqual(suggestion.state, "approved")
        self.assertTrue(suggestion.order_id)
        self.assertEqual(result["res_model"], "tms.order")

    def test_suggestion_approve_without_vehicle_raises(self):
        """Test that approving without vehicle raises error."""
        suggestion = self.env["tms.route.suggestion"].create(
            {
                "name": "Test Suggestion",
                "config_id": self.config.id,
                "planning_date": datetime.now().date(),
                # No vehicle_id or vehicle_type_id
            }
        )

        with self.assertRaises(UserError):
            suggestion.action_approve()

    def test_suggestion_approve_with_vehicle_type_finds_vehicle(self):
        """Test that approving with vehicle type finds a vehicle."""
        suggestion = self.env["tms.route.suggestion"].create(
            {
                "name": "Test Suggestion",
                "config_id": self.config.id,
                "planning_date": datetime.now().date(),
                "vehicle_type_id": self.vehicle_type.id,
                "stop_ids": [(6, 0, [self.stop1.id])],
            }
        )

        suggestion.action_approve()

        self.assertEqual(suggestion.state, "approved")
        self.assertEqual(suggestion.vehicle_id, self.vehicle)

    def test_get_available_vehicle_for_type(self):
        """Test finding available vehicle by type."""
        suggestion = self.env["tms.route.suggestion"].create(
            {
                "name": "Test Suggestion",
                "config_id": self.config.id,
                "planning_date": datetime.now().date(),
                "vehicle_type_id": self.vehicle_type.id,
            }
        )

        vehicle = suggestion._get_available_vehicle_for_type()

        self.assertEqual(vehicle, self.vehicle)

    def test_suggestion_view_on_map_no_url_raises(self):
        """Test that viewing on map without URL raises error."""
        suggestion = self.env["tms.route.suggestion"].create(
            {
                "name": "Test Suggestion",
                "config_id": self.config.id,
                "planning_date": datetime.now().date(),
            }
        )

        with self.assertRaises(UserError):
            suggestion.action_view_on_map()

    def test_suggestion_view_on_map_with_url(self):
        """Test viewing suggestion on map with URL."""
        suggestion = self.env["tms.route.suggestion"].create(
            {
                "name": "Test Suggestion",
                "config_id": self.config.id,
                "planning_date": datetime.now().date(),
                "google_maps_url": "https://maps.google.com/?q=test",
            }
        )

        result = suggestion.action_view_on_map()

        self.assertEqual(result["type"], "ir.actions.act_url")
        self.assertEqual(result["url"], "https://maps.google.com/?q=test")


class TestTMSOrderOptimization(TransactionCase):
    """Test the tms.order optimization fields."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create team
        cls.team = cls.env["tms.team"].create({"name": "Test Team"})

        # Create depot
        cls.depot = cls.env["res.partner"].create(
            {
                "name": "Test Depot",
                "partner_latitude": -23.5505,
                "partner_longitude": -46.6333,
            }
        )

        # Create partner
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Partner 1",
                "partner_latitude": -23.5500,
                "partner_longitude": -46.6300,
            }
        )

    def test_order_lock_field(self):
        """Test the is_locked_for_optimization field."""
        order = self.env["tms.order"].create(
            {
                "name": "Test Order",
                "tms_team_id": self.team.id,
                "origin_id": self.depot.id,
            }
        )

        self.assertFalse(order.is_locked_for_optimization)

        order.is_locked_for_optimization = True

        self.assertTrue(order.is_locked_for_optimization)

    def test_order_can_recalculate_unlocked(self):
        """Test can_recalculate for unlocked order."""
        order = self.env["tms.order"].create(
            {
                "name": "Test Order",
                "tms_team_id": self.team.id,
                "origin_id": self.depot.id,
            }
        )

        # Should be recalculable by default
        self.assertTrue(order.can_recalculate)

    def test_order_can_recalculate_locked(self):
        """Test can_recalculate for locked order."""
        order = self.env["tms.order"].create(
            {
                "name": "Test Order",
                "tms_team_id": self.team.id,
                "origin_id": self.depot.id,
                "is_locked_for_optimization": True,
            }
        )

        self.assertFalse(order.can_recalculate)

    def test_order_can_recalculate_completed_stage(self):
        """Test can_recalculate for order in completed stage."""
        # Find or create a completed stage
        completed_stage = self.env["tms.stage"].search(
            [
                ("is_completed", "=", True),
                ("stage_type", "=", "order"),
            ],
            limit=1,
        )

        if not completed_stage:
            completed_stage = self.env["tms.stage"].create(
                {
                    "name": "Completed",
                    "stage_type": "order",
                    "is_completed": True,
                }
            )

        order = self.env["tms.order"].create(
            {
                "name": "Test Order",
                "tms_team_id": self.team.id,
                "origin_id": self.depot.id,
                "stage_id": completed_stage.id,
            }
        )

        self.assertFalse(order.can_recalculate)
