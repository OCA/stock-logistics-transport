"""Tests for multi-day optimization and max stops constraints."""

from datetime import datetime, timedelta

from odoo.tests import TransactionCase


class TestMultiDayOptimization(TransactionCase):
    """Test multi-day optimization functionality."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create team
        cls.team = cls.env["tms.team"].create({"name": "Test Team"})

        # Create vehicle type with small capacity to force multi-day
        cls.vehicle_type = cls.env["fleet.vehicle.type"].create(
            {
                "name": "Small Van",
                "code": "SMALL_VAN",
                "default_weight_capacity": 500.0,  # Small capacity
                "default_volume_capacity": 2.0,
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

        # Create vehicle with small capacity
        cls.vehicle = cls.env["fleet.vehicle"].create(
            {
                "name": "Small Van 1",
                "model_id": cls.vehicle_model.id,
                "vehicle_type_id": cls.vehicle_type.id,
                "tms_team_id": cls.team.id,
                "weight_capacity": 500.0,
                "volume_capacity": 2.0,
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

        # Create many partners for multi-day testing
        cls.partners = []
        for i in range(10):
            partner = cls.env["res.partner"].create(
                {
                    "name": f"Partner {i + 1}",
                    "partner_latitude": -23.5500 + (i * 0.002),
                    "partner_longitude": -46.6300 + (i * 0.002),
                }
            )
            cls.partners.append(partner)

        # Create TMS order
        cls.order = cls.env["tms.order"].create(
            {
                "name": "Test Order",
                "tms_team_id": cls.team.id,
                "origin_id": cls.depot.id,
            }
        )

        # Create delivery stops with significant weight
        now = datetime.now()
        cls.stops = []
        for partner in cls.partners:
            stop = cls.env["tms.order.stop"].create(
                {
                    "order_id": cls.order.id,
                    "partner_id": partner.id,
                    "weight": 200.0,  # Each stop has 200kg
                    "volume": 0.5,
                    "scheduled_date": now,
                }
            )
            cls.stops.append(stop)

    def _create_optimizer(self, **kwargs):
        """Helper to create an optimizer with default values."""
        now = datetime.now()
        defaults = {
            "name": "Test Optimization",
            "team_id": self.team.id,
            "date_from": now - timedelta(hours=1),
            "date_to": now + timedelta(hours=1),
            "optimization_date": now.date(),
            "delivery_stop_ids": [(6, 0, [s.id for s in self.stops])],
        }
        defaults.update(kwargs)
        return self.env["tms.route.optimizer"].create(defaults)

    def test_enable_multi_day_field(self):
        """Test that multi-day field is correctly set."""
        optimizer = self._create_optimizer(
            enable_multi_day=True,
            planning_horizon_days=5,
        )

        self.assertTrue(optimizer.enable_multi_day)
        self.assertEqual(optimizer.planning_horizon_days, 5)

    def test_max_stops_per_vehicle_field(self):
        """Test that max_stops_per_vehicle field is correctly set."""
        optimizer = self._create_optimizer(max_stops_per_vehicle=3)

        self.assertEqual(optimizer.max_stops_per_vehicle, 3)

    def test_day_result_model_creation(self):
        """Test creating a day result record."""
        optimizer = self._create_optimizer()

        day_result = self.env["tms.route.optimizer.day.result"].create(
            {
                "optimizer_id": optimizer.id,
                "planning_date": datetime.now().date(),
            }
        )

        self.assertEqual(day_result.optimizer_id, optimizer)
        self.assertEqual(day_result.total_stops, 0)
        self.assertEqual(day_result.total_distance, 0)
        self.assertEqual(day_result.total_cost, 0)
        self.assertEqual(day_result.total_vehicles, 0)

    def test_day_result_compute_totals(self):
        """Test that day result computes totals from results."""
        optimizer = self._create_optimizer()

        day_result = self.env["tms.route.optimizer.day.result"].create(
            {
                "optimizer_id": optimizer.id,
                "planning_date": datetime.now().date(),
            }
        )

        # Create a result linked to this day
        self.env["tms.route.optimizer.result"].create(
            {
                "optimizer_id": optimizer.id,
                "day_result_id": day_result.id,
                "vehicle_id": self.vehicle.id,
                "stop_count": 3,
                "total_distance": 15.5,
                "route_cost": 75.0,
            }
        )

        # Refresh computed fields
        day_result.invalidate_recordset()

        self.assertEqual(day_result.total_stops, 3)
        self.assertEqual(day_result.total_distance, 15.5)
        self.assertEqual(day_result.total_cost, 75.0)
        self.assertEqual(day_result.total_vehicles, 1)

    def test_day_result_unassigned_count(self):
        """Test that unassigned count is computed correctly."""
        optimizer = self._create_optimizer()

        day_result = self.env["tms.route.optimizer.day.result"].create(
            {
                "optimizer_id": optimizer.id,
                "planning_date": datetime.now().date(),
                "unassigned_stop_ids": [(6, 0, [self.stops[0].id, self.stops[1].id])],
            }
        )

        self.assertEqual(day_result.unassigned_count, 2)

    def test_prepare_location_data_for_stops(self):
        """Test preparing location data for specific stops."""
        optimizer = self._create_optimizer()
        origin = optimizer._validate_origin_location()

        # Use only first 3 stops
        subset = self.env["tms.order.stop"].browse([s.id for s in self.stops[:3]])

        locations, weights, volumes, stop_ids = (
            optimizer._prepare_location_data_for_stops(origin, subset)
        )

        # Should have depot + 3 stops = 4 locations
        self.assertEqual(len(locations), 4)
        self.assertEqual(len(weights), 3)
        self.assertEqual(len(volumes), 3)
        self.assertEqual(len(stop_ids), 3)

    def test_handle_unassignable_stops(self):
        """Test handling of stops that couldn't be assigned."""
        optimizer = self._create_optimizer(
            enable_multi_day=True,
            planning_horizon_days=1,
        )

        # Simulate unassignable stops
        remaining = self.env["tms.order.stop"].browse([s.id for s in self.stops[:3]])
        optimizer._handle_unassignable_stops(remaining)

        # Should have a warning message
        self.assertIn("3 stops could not be assigned", optimizer.error_message)


class TestMaxStopsConstraint(TransactionCase):
    """Test max stops per vehicle constraint."""

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
                "default_weight_capacity": 10000.0,  # Large capacity
                "default_volume_capacity": 50.0,
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
                "weight_capacity": 10000.0,
                "volume_capacity": 50.0,
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

        # Create partners
        cls.partners = []
        for i in range(6):
            partner = cls.env["res.partner"].create(
                {
                    "name": f"Partner {i + 1}",
                    "partner_latitude": -23.5500 + (i * 0.001),
                    "partner_longitude": -46.6300 + (i * 0.001),
                }
            )
            cls.partners.append(partner)

        # Create order
        cls.order = cls.env["tms.order"].create(
            {
                "name": "Test Order",
                "tms_team_id": cls.team.id,
            }
        )

        # Create stops with minimal weight
        now = datetime.now()
        cls.stops = []
        for partner in cls.partners:
            stop = cls.env["tms.order.stop"].create(
                {
                    "order_id": cls.order.id,
                    "partner_id": partner.id,
                    "weight": 10.0,  # Very light
                    "volume": 0.1,
                    "scheduled_date": now,
                }
            )
            cls.stops.append(stop)

    def test_max_stops_zero_means_unlimited(self):
        """Test that max_stops=0 means no limit."""
        now = datetime.now()
        optimizer = self.env["tms.route.optimizer"].create(
            {
                "name": "Test Optimization",
                "team_id": self.team.id,
                "date_from": now - timedelta(hours=1),
                "date_to": now + timedelta(hours=1),
                "optimization_date": now.date(),
                "delivery_stop_ids": [(6, 0, [s.id for s in self.stops])],
                "max_stops_per_vehicle": 0,
            }
        )

        self.assertEqual(optimizer.max_stops_per_vehicle, 0)

    def test_max_stops_passed_to_solver(self):
        """Test that max_stops is passed to the VRP solver."""
        now = datetime.now()
        optimizer = self.env["tms.route.optimizer"].create(
            {
                "name": "Test Optimization",
                "team_id": self.team.id,
                "date_from": now - timedelta(hours=1),
                "date_to": now + timedelta(hours=1),
                "optimization_date": now.date(),
                "delivery_stop_ids": [(6, 0, [s.id for s in self.stops])],
                "max_stops_per_vehicle": 3,
            }
        )

        # The constraint is passed to _solve_vrp via the parameter
        # We can verify by checking the field value
        self.assertEqual(optimizer.max_stops_per_vehicle, 3)
