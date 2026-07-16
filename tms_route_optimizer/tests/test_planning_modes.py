"""Tests for the new planning modes functionality."""

from datetime import datetime, timedelta

from odoo.exceptions import UserError
from odoo.tests import TransactionCase


class TestPlanningModes(TransactionCase):
    """Test the three planning modes: team, vehicles, vehicle_types."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create team
        cls.team = cls.env["tms.team"].create({"name": "Test Team"})

        # Create vehicle types with unique codes to avoid conflicts with demo data
        cls.vehicle_type_van = cls.env["fleet.vehicle.type"].create(
            {
                "name": "Test Van PM",
                "code": "TEST_VAN_PM",
                "default_weight_capacity": 1500.0,
                "default_volume_capacity": 8.0,
                "default_cost_per_km": 2.50,
                "default_minimum_trip_cost": 50.0,
            }
        )

        cls.vehicle_type_truck = cls.env["fleet.vehicle.type"].create(
            {
                "name": "Test Truck PM",
                "code": "TEST_TRUCK_PM",
                "default_weight_capacity": 5000.0,
                "default_volume_capacity": 25.0,
                "default_cost_per_km": 4.00,
                "default_minimum_trip_cost": 100.0,
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

        # Create vehicles
        cls.vehicle1 = cls.env["fleet.vehicle"].create(
            {
                "name": "Van 1",
                "model_id": cls.vehicle_model.id,
                "vehicle_type_id": cls.vehicle_type_van.id,
                "tms_team_id": cls.team.id,
                "weight_capacity": 1500.0,
                "volume_capacity": 8.0,
                "cost_per_km": 2.50,
                "minimum_trip_cost": 50.0,
            }
        )

        cls.vehicle2 = cls.env["fleet.vehicle"].create(
            {
                "name": "Truck 1",
                "model_id": cls.vehicle_model.id,
                "vehicle_type_id": cls.vehicle_type_truck.id,
                "tms_team_id": cls.team.id,
                "weight_capacity": 5000.0,
                "volume_capacity": 25.0,
                "cost_per_km": 4.00,
                "minimum_trip_cost": 100.0,
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
        cls.partners = []
        for i in range(5):
            partner = cls.env["res.partner"].create(
                {
                    "name": f"Partner {i + 1}",
                    "partner_latitude": -23.5500 + (i * 0.001),
                    "partner_longitude": -46.6300 + (i * 0.001),
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

        # Create delivery stops
        now = datetime.now()
        cls.stops = []
        for i, partner in enumerate(cls.partners):
            stop = cls.env["tms.order.stop"].create(
                {
                    "order_id": cls.order.id,
                    "partner_id": partner.id,
                    "weight": 100.0 * (i + 1),
                    "volume": 0.5 * (i + 1),
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

    def test_planning_mode_default(self):
        """Test that default planning mode is 'team'."""
        optimizer = self._create_optimizer()
        self.assertEqual(optimizer.planning_mode, "team")

    def test_planning_mode_team(self):
        """Test planning mode by team."""
        optimizer = self._create_optimizer(planning_mode="team")

        # _get_vehicles_for_optimization should return team vehicles
        vehicles = optimizer._get_vehicles_for_optimization()

        self.assertEqual(len(vehicles), 2)
        self.assertIn(self.vehicle1, vehicles)
        self.assertIn(self.vehicle2, vehicles)

    def test_planning_mode_vehicles(self):
        """Test planning mode by specific vehicles."""
        optimizer = self._create_optimizer(
            planning_mode="vehicles",
            vehicle_ids=[(6, 0, [self.vehicle1.id])],
        )

        vehicles = optimizer._get_vehicles_for_optimization()

        self.assertEqual(len(vehicles), 1)
        self.assertEqual(vehicles[0], self.vehicle1)

    def test_planning_mode_vehicles_empty_raises(self):
        """Test that vehicles mode raises error if no vehicles selected."""
        optimizer = self._create_optimizer(planning_mode="vehicles")

        with self.assertRaises(UserError):
            optimizer._get_vehicles_for_optimization()

    def test_planning_mode_vehicle_types(self):
        """Test planning mode by vehicle types."""
        optimizer = self._create_optimizer(
            planning_mode="vehicle_types",
            vehicle_type_ids=[(6, 0, [self.vehicle_type_van.id])],
            vehicles_per_type=3,
        )

        # For vehicle_types mode, _get_vehicles_for_optimization returns None
        # and we use _prepare_vehicle_data_from_types instead
        result = optimizer._get_vehicles_for_optimization()
        self.assertIsNone(result)

        # Get virtual vehicle data
        (
            capacities_weight,
            capacities_volume,
            cost_per_km,
            min_cost,
            type_mapping,
        ) = optimizer._prepare_vehicle_data_from_types()

        # Should have 3 virtual vehicles (vehicles_per_type=3)
        self.assertEqual(len(capacities_weight), 3)
        self.assertEqual(len(capacities_volume), 3)
        self.assertEqual(len(cost_per_km), 3)
        self.assertEqual(len(min_cost), 3)
        self.assertEqual(len(type_mapping), 3)

        # All should have van capacities
        for cap in capacities_weight:
            self.assertEqual(cap, 1500.0)
        for cap in capacities_volume:
            self.assertEqual(cap, 8.0)

    def test_planning_mode_vehicle_types_multiple(self):
        """Test vehicle types mode with multiple types."""
        optimizer = self._create_optimizer(
            planning_mode="vehicle_types",
            vehicle_type_ids=[
                (
                    6,
                    0,
                    [
                        self.vehicle_type_van.id,
                        self.vehicle_type_truck.id,
                    ],
                )
            ],
            vehicles_per_type=2,
        )

        (
            capacities_weight,
            capacities_volume,
            _,
            _,
            type_mapping,
        ) = optimizer._prepare_vehicle_data_from_types()

        # Should have 4 virtual vehicles (2 types * 2 per type)
        self.assertEqual(len(capacities_weight), 4)

        # First 2 should be vans, next 2 should be trucks
        self.assertEqual(type_mapping[0], self.vehicle_type_van.id)
        self.assertEqual(type_mapping[1], self.vehicle_type_van.id)
        self.assertEqual(type_mapping[2], self.vehicle_type_truck.id)
        self.assertEqual(type_mapping[3], self.vehicle_type_truck.id)

    def test_planning_mode_vehicle_types_empty_raises(self):
        """Test that vehicle types mode raises error if no types selected."""
        optimizer = self._create_optimizer(planning_mode="vehicle_types")

        with self.assertRaises(UserError):
            optimizer._prepare_vehicle_data_from_types()

    def test_get_vehicle_for_type(self):
        """Test finding a vehicle by type."""
        optimizer = self._create_optimizer()

        vehicle = optimizer._get_vehicle_for_type(self.vehicle_type_van.id)
        self.assertEqual(vehicle, self.vehicle1)

        vehicle = optimizer._get_vehicle_for_type(self.vehicle_type_truck.id)
        self.assertEqual(vehicle, self.vehicle2)

    def test_get_vehicle_for_type_not_found(self):
        """Test that no vehicle is returned for non-existent type."""
        optimizer = self._create_optimizer()

        # Create a type with no vehicles
        new_type = self.env["fleet.vehicle.type"].create(
            {
                "name": "Empty Type",
                "code": "EMPTY",
            }
        )

        vehicle = optimizer._get_vehicle_for_type(new_type.id)
        self.assertFalse(vehicle)
