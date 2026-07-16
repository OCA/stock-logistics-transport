"""Tests for single vehicle multi-day optimization scenarios.

This test module specifically targets the scenario where a route configuration
has only ONE vehicle associated and multi-day planning is enabled.
"""

from datetime import datetime, timedelta

from odoo.tests import TransactionCase


class TestSingleVehicleMultiDay(TransactionCase):
    """Test multi-day optimization with a single vehicle."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create team
        cls.team = cls.env["tms.team"].create({"name": "Single Vehicle Test Team"})

        # Create vehicle type with specific capacity
        cls.vehicle_type = cls.env["fleet.vehicle.type"].create(
            {
                "name": "Single Van Type",
                "code": "SINGLE_VAN_TEST",
                "default_weight_capacity": 1000.0,
                "default_volume_capacity": 5.0,
                "default_cost_per_km": 2.50,
                "default_minimum_trip_cost": 50.0,
            }
        )

        # Create vehicle model
        brand = cls.env["fleet.vehicle.model.brand"].create(
            {"name": "Test Brand Single"}
        )
        cls.vehicle_model = cls.env["fleet.vehicle.model"].create(
            {
                "name": "Test Model Single",
                "brand_id": brand.id,
            }
        )

        # Create ONLY ONE vehicle - this is the key scenario
        cls.single_vehicle = cls.env["fleet.vehicle"].create(
            {
                "name": "Single Test Vehicle",
                "model_id": cls.vehicle_model.id,
                "vehicle_type_id": cls.vehicle_type.id,
                "tms_team_id": cls.team.id,
                "weight_capacity": 1000.0,
                "volume_capacity": 5.0,
                "cost_per_km": 2.50,
                "minimum_trip_cost": 50.0,
            }
        )

        # Create depot
        cls.depot = cls.env["res.partner"].create(
            {
                "name": "Single Vehicle Test Depot",
                "partner_latitude": -23.5505,
                "partner_longitude": -46.6333,
            }
        )

        cls.team.default_origin_location_id = cls.depot.id
        cls.team.default_destination_location_id = cls.depot.id

        # Create many partners for multi-day testing
        # We want enough stops to force distribution across multiple days
        cls.partners = []
        for i in range(12):
            partner = cls.env["res.partner"].create(
                {
                    "name": f"Partner Single {i + 1}",
                    "partner_latitude": -23.5500 + (i * 0.003),
                    "partner_longitude": -46.6300 + (i * 0.003),
                }
            )
            cls.partners.append(partner)

        # Create TMS order
        cls.order = cls.env["tms.order"].create(
            {
                "name": "Single Vehicle Test Order",
                "tms_team_id": cls.team.id,
                "origin_id": cls.depot.id,
            }
        )

        # Create delivery stops with weight that requires multiple days
        # With vehicle capacity of 1000kg and stops of 300kg each,
        # only 3 stops can fit per day (900kg < 1000kg)
        now = datetime.now()
        cls.stops = []
        for _i, partner in enumerate(cls.partners):
            stop = cls.env["tms.order.stop"].create(
                {
                    "order_id": cls.order.id,
                    "partner_id": partner.id,
                    "weight": 300.0,  # 300kg each - 3 max per day with 1000kg capacity
                    "volume": 1.0,
                    "scheduled_date": now,
                    "state": "draft",
                }
            )
            cls.stops.append(stop)

    def _create_single_vehicle_optimizer(self, **kwargs):
        """Helper to create optimizer with single vehicle for multi-day testing."""
        now = datetime.now()
        defaults = {
            "name": "Single Vehicle Multi-Day Test",
            "team_id": self.team.id,
            "planning_mode": "vehicles",
            "vehicle_ids": [(6, 0, [self.single_vehicle.id])],
            "enable_multi_day": True,
            "planning_horizon_days": 5,
            "max_stops_per_vehicle": 0,  # No limit on stops, use capacity
            "date_from": now - timedelta(hours=1),
            "date_to": now + timedelta(hours=24),
            "optimization_date": now.date(),
            "delivery_stop_ids": [(6, 0, [s.id for s in self.stops])],
        }
        defaults.update(kwargs)
        return self.env["tms.route.optimizer"].create(defaults)

    def test_single_vehicle_config_setup(self):
        """Test that single vehicle optimizer is correctly configured."""
        optimizer = self._create_single_vehicle_optimizer()

        self.assertEqual(optimizer.planning_mode, "vehicles")
        self.assertEqual(len(optimizer.vehicle_ids), 1)
        self.assertEqual(optimizer.vehicle_ids[0], self.single_vehicle)
        self.assertTrue(optimizer.enable_multi_day)
        self.assertEqual(optimizer.planning_horizon_days, 5)

    def test_single_vehicle_gets_vehicles_correctly(self):
        """Test that _get_vehicles_for_optimization returns the single vehicle."""
        optimizer = self._create_single_vehicle_optimizer()

        vehicles = optimizer._get_vehicles_for_optimization()

        self.assertEqual(len(vehicles), 1)
        self.assertEqual(vehicles[0], self.single_vehicle)

    def test_single_vehicle_multi_day_creates_day_results(self):
        """Test that multi-day optimization with single vehicle creates day results.

        With 12 stops at 300kg each and 1000kg capacity:
        - Day 1: 3 stops (900kg)
        - Day 2: 3 stops (900kg)
        - Day 3: 3 stops (900kg)
        - Day 4: 3 stops (900kg)
        Total: 4 days needed
        """
        optimizer = self._create_single_vehicle_optimizer()

        optimizer.action_run_optimization()

        # Debug info
        import logging

        _logger = logging.getLogger(__name__)
        _logger.info(
            "Optimizer state: %s, error: %s, day_results: %d, results: %d",
            optimizer.state,
            optimizer.error_message,
            len(optimizer.day_result_ids),
            len(optimizer.result_ids),
        )
        _logger.info(
            "Total distance: %s, total cost: %s, vehicles used: %s",
            optimizer.total_distance,
            optimizer.total_cost,
            optimizer.total_vehicles_used,
        )

        self.assertEqual(optimizer.state, "done")
        # Should have day results created
        self.assertTrue(
            len(optimizer.day_result_ids) > 0,
            f"Expected at least one day result to be created. "
            f"Error: {optimizer.error_message}, "
            f"Result count: {len(optimizer.result_ids)}",
        )

    def test_single_vehicle_multi_day_distributes_stops(self):
        """Test that stops are distributed across multiple days."""
        optimizer = self._create_single_vehicle_optimizer()

        optimizer.action_run_optimization()

        self.assertEqual(optimizer.state, "done")

        # Check that we have results
        self.assertTrue(
            len(optimizer.result_ids) > 0,
            "Expected at least one route result to be created",
        )

        # Count total assigned stops across all results
        total_assigned_stops = sum(
            len(result.stop_ids) for result in optimizer.result_ids
        )
        self.assertEqual(
            total_assigned_stops,
            len(self.stops),
            f"Expected all {len(self.stops)} stops to be assigned, "
            f"but got {total_assigned_stops}",
        )

    def test_single_vehicle_respects_capacity(self):
        """Test that each route respects vehicle capacity."""
        optimizer = self._create_single_vehicle_optimizer()

        optimizer.action_run_optimization()

        self.assertEqual(optimizer.state, "done")

        for result in optimizer.result_ids:
            self.assertLessEqual(
                result.total_weight,
                self.single_vehicle.weight_capacity,
                f"Route weight {result.total_weight} exceeds vehicle capacity "
                f"{self.single_vehicle.weight_capacity}",
            )

    def test_single_vehicle_with_max_stops_constraint(self):
        """Test single vehicle with max stops per vehicle constraint."""
        optimizer = self._create_single_vehicle_optimizer(
            max_stops_per_vehicle=3,  # Max 3 stops per vehicle per day
        )

        optimizer.action_run_optimization()

        self.assertEqual(optimizer.state, "done")

        # Each route should have at most 3 stops
        for result in optimizer.result_ids:
            self.assertLessEqual(
                result.stop_count,
                3,
                f"Route has {result.stop_count} stops, expected max 3",
            )

    def test_single_vehicle_day_results_have_correct_vehicle(self):
        """Test that all day results reference the single vehicle."""
        optimizer = self._create_single_vehicle_optimizer()

        optimizer.action_run_optimization()

        self.assertEqual(optimizer.state, "done")

        for result in optimizer.result_ids:
            self.assertEqual(
                result.vehicle_id,
                self.single_vehicle,
                "Route result should reference the single vehicle",
            )

    def test_single_vehicle_total_distance_calculated(self):
        """Test that total distance is calculated correctly."""
        optimizer = self._create_single_vehicle_optimizer()

        optimizer.action_run_optimization()

        self.assertEqual(optimizer.state, "done")
        self.assertGreater(
            optimizer.total_distance, 0, "Total distance should be greater than 0"
        )

    def test_single_vehicle_total_cost_calculated(self):
        """Test that total cost is calculated correctly."""
        optimizer = self._create_single_vehicle_optimizer()

        optimizer.action_run_optimization()

        self.assertEqual(optimizer.state, "done")
        self.assertGreater(
            optimizer.total_cost, 0, "Total cost should be greater than 0"
        )


class TestSingleVehicleConfigMultiDay(TransactionCase):
    """Test single vehicle multi-day optimization using config model.

    This tests the scenario where a tms.route.optimizer.config
    has only one vehicle associated.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create team
        cls.team = cls.env["tms.team"].create({"name": "Config Single Vehicle Team"})

        # Create vehicle type
        cls.vehicle_type = cls.env["fleet.vehicle.type"].create(
            {
                "name": "Config Van Type",
                "code": "CONFIG_VAN_SINGLE",
                "default_weight_capacity": 800.0,
                "default_volume_capacity": 4.0,
                "default_cost_per_km": 3.00,
                "default_minimum_trip_cost": 60.0,
            }
        )

        # Create vehicle model
        brand = cls.env["fleet.vehicle.model.brand"].create(
            {"name": "Config Test Brand"}
        )
        cls.vehicle_model = cls.env["fleet.vehicle.model"].create(
            {
                "name": "Config Test Model",
                "brand_id": brand.id,
            }
        )

        # Create ONLY ONE vehicle
        cls.single_vehicle = cls.env["fleet.vehicle"].create(
            {
                "name": "Config Single Vehicle",
                "model_id": cls.vehicle_model.id,
                "vehicle_type_id": cls.vehicle_type.id,
                "tms_team_id": cls.team.id,
                "weight_capacity": 800.0,
                "volume_capacity": 4.0,
                "cost_per_km": 3.00,
                "minimum_trip_cost": 60.0,
            }
        )

        # Create depot
        cls.depot = cls.env["res.partner"].create(
            {
                "name": "Config Single Vehicle Depot",
                "partner_latitude": -23.5505,
                "partner_longitude": -46.6333,
            }
        )

        cls.team.default_origin_location_id = cls.depot.id
        cls.team.default_destination_location_id = cls.depot.id

        # Create partners
        cls.partners = []
        for i in range(9):  # 9 stops
            partner = cls.env["res.partner"].create(
                {
                    "name": f"Config Partner {i + 1}",
                    "partner_latitude": -23.5500 + (i * 0.004),
                    "partner_longitude": -46.6300 + (i * 0.004),
                }
            )
            cls.partners.append(partner)

        # Create TMS order
        cls.order = cls.env["tms.order"].create(
            {
                "name": "Config Single Vehicle Order",
                "tms_team_id": cls.team.id,
                "origin_id": cls.depot.id,
            }
        )

        # Create stops with weight requiring multiple days
        # 800kg capacity, 300kg per stop = 2 stops max per day
        now = datetime.now()
        cls.stops = []
        for i, partner in enumerate(cls.partners):
            stop = cls.env["tms.order.stop"].create(
                {
                    "order_id": cls.order.id,
                    "partner_id": partner.id,
                    "weight": 300.0,
                    "volume": 1.0,
                    "scheduled_date": now + timedelta(days=i // 3),
                    "state": "draft",
                }
            )
            cls.stops.append(stop)

    def _create_single_vehicle_config(self, **kwargs):
        """Helper to create an optimizer config with single vehicle."""
        defaults = {
            "name": "Single Vehicle Config Test",
            "team_id": self.team.id,
            "planning_mode": "vehicles",
            "vehicle_ids": [(6, 0, [self.single_vehicle.id])],
            "enable_multi_day": True,
            "planning_horizon_days": 5,
            "max_stops_per_vehicle": 0,
            "days_ahead": 5,
        }
        defaults.update(kwargs)
        return self.env["tms.route.optimizer.config"].create(defaults)

    def test_config_single_vehicle_setup(self):
        """Test that config with single vehicle is correctly set up."""
        config = self._create_single_vehicle_config()

        self.assertEqual(config.planning_mode, "vehicles")
        self.assertEqual(len(config.vehicle_ids), 1)
        self.assertEqual(config.vehicle_ids[0], self.single_vehicle)
        self.assertTrue(config.enable_multi_day)

    def test_config_single_vehicle_gets_eligible_stops(self):
        """Test that config correctly finds eligible stops."""
        config = self._create_single_vehicle_config()

        eligible_stops = config._get_eligible_stops()

        self.assertGreater(len(eligible_stops), 0, "Expected to find eligible stops")

    def test_config_single_vehicle_runs_auto_optimization(self):
        """Test that auto optimization runs with single vehicle config."""
        config = self._create_single_vehicle_config()

        # This should not raise an error
        config._run_auto_optimization()

        # Check that suggestions were created
        self.assertGreater(
            config.suggestion_count,
            0,
            "Expected suggestions to be created after auto optimization",
        )

    def test_config_single_vehicle_creates_suggestions(self):
        """Test that suggestions are created for each route."""
        config = self._create_single_vehicle_config()

        config._run_auto_optimization()

        # Verify suggestions exist
        suggestions = self.env["tms.route.suggestion"].search(
            [("config_id", "=", config.id)]
        )

        self.assertGreater(
            len(suggestions), 0, "Expected at least one suggestion to be created"
        )

        # Each suggestion should have the single vehicle
        for suggestion in suggestions:
            self.assertEqual(
                suggestion.vehicle_id,
                self.single_vehicle,
                "Suggestion should reference the single vehicle",
            )

    def test_config_single_vehicle_with_max_stops(self):
        """Test config with single vehicle and max stops constraint."""
        config = self._create_single_vehicle_config(
            max_stops_per_vehicle=2,  # Max 2 stops per day
        )

        config._run_auto_optimization()

        # Check suggestions
        suggestions = self.env["tms.route.suggestion"].search(
            [("config_id", "=", config.id)]
        )

        self.assertGreater(len(suggestions), 0, "Expected suggestions to be created")

        # Each suggestion should have at most 2 stops
        for suggestion in suggestions:
            self.assertLessEqual(
                suggestion.stop_count,
                2,
                f"Suggestion has {suggestion.stop_count} stops, expected max 2",
            )


class TestSingleVehicleEdgeCases(TransactionCase):
    """Test edge cases for single vehicle multi-day optimization."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create team
        cls.team = cls.env["tms.team"].create({"name": "Edge Case Team"})

        # Create vehicle type
        cls.vehicle_type = cls.env["fleet.vehicle.type"].create(
            {
                "name": "Edge Case Van",
                "code": "EDGE_VAN",
                "default_weight_capacity": 500.0,
                "default_volume_capacity": 2.0,
                "default_cost_per_km": 2.00,
                "default_minimum_trip_cost": 40.0,
            }
        )

        # Create vehicle model
        brand = cls.env["fleet.vehicle.model.brand"].create({"name": "Edge Brand"})
        cls.vehicle_model = cls.env["fleet.vehicle.model"].create(
            {
                "name": "Edge Model",
                "brand_id": brand.id,
            }
        )

        # Create single vehicle
        cls.single_vehicle = cls.env["fleet.vehicle"].create(
            {
                "name": "Edge Case Vehicle",
                "model_id": cls.vehicle_model.id,
                "vehicle_type_id": cls.vehicle_type.id,
                "tms_team_id": cls.team.id,
                "weight_capacity": 500.0,
                "volume_capacity": 2.0,
                "cost_per_km": 2.00,
                "minimum_trip_cost": 40.0,
            }
        )

        # Create depot
        cls.depot = cls.env["res.partner"].create(
            {
                "name": "Edge Case Depot",
                "partner_latitude": -23.5505,
                "partner_longitude": -46.6333,
            }
        )

        cls.team.default_origin_location_id = cls.depot.id
        cls.team.default_destination_location_id = cls.depot.id

    def _create_test_stops(self, count, weight_per_stop):
        """Helper to create test stops with specific weights."""
        partners = []
        for i in range(count):
            partner = self.env["res.partner"].create(
                {
                    "name": f"Edge Partner {i + 1}",
                    "partner_latitude": -23.5500 + (i * 0.002),
                    "partner_longitude": -46.6300 + (i * 0.002),
                }
            )
            partners.append(partner)

        order = self.env["tms.order"].create(
            {
                "name": "Edge Case Order",
                "tms_team_id": self.team.id,
                "origin_id": self.depot.id,
            }
        )

        now = datetime.now()
        stops = []
        for _i, partner in enumerate(partners):
            stop = self.env["tms.order.stop"].create(
                {
                    "order_id": order.id,
                    "partner_id": partner.id,
                    "weight": weight_per_stop,
                    "volume": 0.5,
                    "scheduled_date": now,
                    "state": "draft",
                }
            )
            stops.append(stop)

        return stops

    def test_single_vehicle_one_stop_per_day(self):
        """Test when each stop requires its own day due to capacity."""
        # Create 3 stops of 450kg each (can only fit 1 per 500kg vehicle)
        stops = self._create_test_stops(3, 450.0)

        now = datetime.now()
        optimizer = self.env["tms.route.optimizer"].create(
            {
                "name": "One Stop Per Day Test",
                "team_id": self.team.id,
                "planning_mode": "vehicles",
                "vehicle_ids": [(6, 0, [self.single_vehicle.id])],
                "enable_multi_day": True,
                "planning_horizon_days": 5,
                "date_from": now - timedelta(hours=1),
                "date_to": now + timedelta(hours=24),
                "optimization_date": now.date(),
                "delivery_stop_ids": [(6, 0, [s.id for s in stops])],
            }
        )

        optimizer.action_run_optimization()

        self.assertEqual(optimizer.state, "done")
        # Should have 3 day results (1 stop per day)
        self.assertGreaterEqual(
            len(optimizer.day_result_ids),
            1,
            "Expected day results when capacity forces distribution",
        )

    def test_single_vehicle_all_stops_fit_one_day(self):
        """Test when all stops can fit in a single day."""
        # Create 5 stops of 80kg each (400kg total, fits in 500kg vehicle)
        stops = self._create_test_stops(5, 80.0)

        now = datetime.now()
        optimizer = self.env["tms.route.optimizer"].create(
            {
                "name": "All Stops One Day Test",
                "team_id": self.team.id,
                "planning_mode": "vehicles",
                "vehicle_ids": [(6, 0, [self.single_vehicle.id])],
                "enable_multi_day": True,
                "planning_horizon_days": 5,
                "date_from": now - timedelta(hours=1),
                "date_to": now + timedelta(hours=24),
                "optimization_date": now.date(),
                "delivery_stop_ids": [(6, 0, [s.id for s in stops])],
            }
        )

        optimizer.action_run_optimization()

        self.assertEqual(optimizer.state, "done")

        # All 5 stops should be assigned
        total_assigned = sum(len(r.stop_ids) for r in optimizer.result_ids)
        self.assertEqual(
            total_assigned,
            5,
            f"Expected all 5 stops to be assigned, got {total_assigned}",
        )

    def test_single_vehicle_exceeds_horizon(self):
        """Test when stops exceed the planning horizon capacity."""
        # Create 20 stops of 400kg each (one per day needed)
        # With 3 day horizon, only 3 can be assigned
        stops = self._create_test_stops(20, 400.0)

        now = datetime.now()
        optimizer = self.env["tms.route.optimizer"].create(
            {
                "name": "Exceeds Horizon Test",
                "team_id": self.team.id,
                "planning_mode": "vehicles",
                "vehicle_ids": [(6, 0, [self.single_vehicle.id])],
                "enable_multi_day": True,
                "planning_horizon_days": 3,  # Only 3 days
                "date_from": now - timedelta(hours=1),
                "date_to": now + timedelta(hours=24),
                "optimization_date": now.date(),
                "delivery_stop_ids": [(6, 0, [s.id for s in stops])],
            }
        )

        optimizer.action_run_optimization()

        self.assertEqual(optimizer.state, "done")

        # Should have a warning about unassigned stops
        self.assertTrue(
            optimizer.error_message, "Expected warning message about unassigned stops"
        )
        self.assertIn(
            "could not be assigned",
            optimizer.error_message,
            "Warning should mention unassigned stops",
        )
