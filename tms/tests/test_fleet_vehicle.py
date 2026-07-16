from odoo.tests.common import TransactionCase


class TestFleetVehicle(TransactionCase):
    @classmethod
    def setUpClass(self):
        super().setUpClass()

        self.uom_volume = self.env.ref("uom.product_uom_cubic_meter")

        self.team = self.env["tms.team"].create(
            {
                "name": "Test Team",
            }
        )

        self.vehicle = self.env["fleet.vehicle"].create(
            {
                "name": "Test Vehicle",
                "capacity": 50,
                "license_plate": "Test Plate",
                "cargo_uom_id": self.uom_volume.id,
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

    def test_vehicle_creation(self):
        self.assertTrue(self.vehicle, "Vehicle wasn't created successfully")
        self.assertEqual(
            self.vehicle.name,
            "Test Brand/Test Model/Test Plate",
            "Vehicle name should be 'Test Vehicle'",
        )
        self.assertEqual(self.vehicle.capacity, 50, "Vehicle capacity should be 5000")
        self.assertEqual(
            self.vehicle.cargo_uom_id,
            self.uom_volume,
            "Vehicle UOM should be correctly assigned",
        )

    def test_default_volume_uom(self):
        self.assertEqual(
            self.vehicle.cargo_uom_id,
            self.uom_volume,
            "Default UOM should be cubic meters",
        )
