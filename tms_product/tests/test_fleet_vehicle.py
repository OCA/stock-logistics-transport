# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.base.tests.common import BaseCommon


class TestFleetVehicle(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.vehicle_model = cls.env["fleet.vehicle.model"].create(
            {
                "name": "Cargo Model",
                "brand_id": cls.env["fleet.vehicle.model.brand"]
                .create({"name": "Cargo Brand"})
                .id,
            }
        )

    def _create_vehicle(self, operation):
        return self.env["fleet.vehicle"].create(
            {
                "name": f"Vehicle {operation}",
                "model_id": self.vehicle_model.id,
                "operation": operation,
                "cargo_type": "volume",
            }
        )

    def test_passenger_operation_clears_cargo_type(self):
        vehicle = self._create_vehicle("cargo")
        vehicle.operation = "passenger"
        self.assertFalse(vehicle.cargo_type)

    def test_cargo_operation_keeps_cargo_type(self):
        vehicle = self._create_vehicle("cargo")
        self.assertEqual(vehicle.cargo_type, "volume")

    def test_transportable_product(self):
        vehicle = self._create_vehicle("cargo")
        transportable = self.env["transportable.product"].create(
            {
                "vehicle_id": vehicle.id,
                "product_id": self.env["product.product"]
                .create({"name": "Cargo Item", "type": "consu"})
                .id,
                "capacity": 10.0,
                "measure_type": "unit",
                "unit_uom": self.env.ref("uom.product_uom_unit").id,
            }
        )
        self.assertEqual(transportable.vehicle_id, vehicle)
        self.assertEqual(transportable.measure_type, "unit")

    def test_driver_action_view_stock_serial_delegates_to_partner(self):
        driver = self.env["tms.driver"].create({"name": "Serial Driver"})
        action = driver.action_view_stock_serial()
        self.assertEqual(action["res_model"], "stock.lot")
