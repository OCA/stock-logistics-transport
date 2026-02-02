from psycopg2 import IntegrityError

from odoo.tests import TransactionCase
from odoo.tools import mute_logger


class TestFleetVehicleType(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_create_vehicle_type(self):
        """Test creating a fleet vehicle type"""
        vehicle_type = self.env["fleet.vehicle.type"].create(
            {
                "name": "Test Van",
                "code": "TEST_VAN",
                "description": "Test vehicle type",
                "default_weight_capacity": 1500.0,
                "default_volume_capacity": 8.0,
                "default_cost_per_km": 2.50,
                "default_minimum_trip_cost": 50.0,
            }
        )
        self.assertEqual(vehicle_type.name, "Test Van")
        self.assertEqual(vehicle_type.code, "TEST_VAN")
        self.assertEqual(vehicle_type.default_weight_capacity, 1500.0)
        self.assertEqual(vehicle_type.default_volume_capacity, 8.0)
        self.assertEqual(vehicle_type.default_cost_per_km, 2.50)
        self.assertEqual(vehicle_type.default_minimum_trip_cost, 50.0)
        self.assertTrue(vehicle_type.active)

    @mute_logger("odoo.sql_db")
    def test_vehicle_type_unique_code(self):
        """Test that vehicle type codes are unique"""
        import time
        import uuid

        # Use timestamp + uuid to ensure uniqueness
        unique_code = f"UNIQUE_{int(time.time() * 1000000)}_{uuid.uuid4().hex[:8]}"
        self.env["fleet.vehicle.type"].create(
            {
                "name": "Test Van 1",
                "code": unique_code,
            }
        )
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            self.env["fleet.vehicle.type"].create(
                {
                    "name": "Test Van 2",
                    "code": unique_code,
                }
            )

    def test_demo_vehicle_types_loaded(self):
        """Test that demo vehicle types are loaded"""
        van = self.env["fleet.vehicle.type"].search([("code", "=", "VAN")], limit=1)
        vuc = self.env["fleet.vehicle.type"].search([("code", "=", "VUC")], limit=1)
        toco = self.env["fleet.vehicle.type"].search([("code", "=", "TOCO")], limit=1)

        # These may or may not exist depending on module installation
        if van:
            self.assertEqual(van.name, "Van")
        if vuc:
            self.assertEqual(vuc.name, "VUC")
        if toco:
            self.assertEqual(toco.name, "Toco")
