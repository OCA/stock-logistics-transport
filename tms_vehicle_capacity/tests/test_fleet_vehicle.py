from odoo.tests import TransactionCase


class TestFleetVehicle(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
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
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Test Depot",
            }
        )
        # Create a vehicle model (required field)
        cls.vehicle_model = cls.env["fleet.vehicle.model"].create(
            {
                "name": "Test Model",
                "brand_id": cls.env["fleet.vehicle.model.brand"].search([], limit=1).id
                or cls.env["fleet.vehicle.model.brand"]
                .create({"name": "Test Brand"})
                .id,
            }
        )

    def test_vehicle_with_type(self):
        """Test creating a fleet vehicle with type"""
        vehicle = self.env["fleet.vehicle"].create(
            {
                "name": "Test Vehicle",
                "model_id": self.vehicle_model.id,
                "vehicle_type_id": self.vehicle_type.id,
                "depot_location_id": self.partner.id,
            }
        )
        self.assertEqual(vehicle.vehicle_type_id.id, self.vehicle_type.id)
        self.assertEqual(vehicle.depot_location_id.id, self.partner.id)

    def test_vehicle_capacity_from_type(self):
        """Test that vehicle capacity is populated from type"""
        vehicle = self.env["fleet.vehicle"].create(
            {
                "name": "Test Vehicle",
                "model_id": self.vehicle_model.id,
                "vehicle_type_id": self.vehicle_type.id,
            }
        )
        # Trigger onchange
        vehicle._onchange_vehicle_type_id()
        self.assertEqual(vehicle.weight_capacity, 1500.0)
        self.assertEqual(vehicle.volume_capacity, 8.0)
        self.assertEqual(vehicle.cost_per_km, 2.50)
        self.assertEqual(vehicle.minimum_trip_cost, 50.0)

    def test_vehicle_custom_capacity(self):
        """Test that vehicle can override type capacity"""
        vehicle = self.env["fleet.vehicle"].create(
            {
                "name": "Test Vehicle",
                "model_id": self.vehicle_model.id,
                "vehicle_type_id": self.vehicle_type.id,
                "weight_capacity": 2000.0,
                "volume_capacity": 10.0,
            }
        )
        self.assertEqual(vehicle.weight_capacity, 2000.0)
        self.assertEqual(vehicle.volume_capacity, 10.0)
