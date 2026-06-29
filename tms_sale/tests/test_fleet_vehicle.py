# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import ValidationError

from odoo.addons.base.tests.common import BaseCommon


class TestFleetVehicleTmsSale(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.vehicle_model = cls.env["fleet.vehicle.model"].create(
            {
                "name": "TMS Model",
                "brand_id": cls.env["fleet.vehicle.model.brand"]
                .create({"name": "TMS Brand"})
                .id,
            }
        )
        cls.trip_service = cls.env.ref("tms_product.product_tms_trip_service")
        cls.seat_service = cls.env.ref("tms_product.product_tms_seat_service")
        cls.trip_product = cls.trip_service.product_variant_ids[0]
        cls.seat_product = cls.seat_service.product_variant_ids[0]

    def _create_vehicle(self, operation, **extra):
        return self.env["fleet.vehicle"].create(
            {
                "name": f"Vehicle {operation}",
                "model_id": self.vehicle_model.id,
                "operation": operation,
                **extra,
            }
        )

    def test_passenger_vehicle_uses_seat_service(self):
        vehicle = self._create_vehicle(
            "passenger",
            tms_service_product_id=self.seat_product.id,
            capacity=40,
        )
        self.assertEqual(vehicle.tms_service_product_id, self.seat_product)
        self.assertEqual(vehicle.tms_service_filter_type, "seat")

    def test_cargo_vehicle_uses_trip_service(self):
        vehicle = self._create_vehicle(
            "cargo",
            tms_service_product_id=self.trip_product.id,
            cargo_type="volume",
        )
        self.assertEqual(vehicle.tms_service_product_id, self.trip_product)
        self.assertEqual(vehicle.tms_service_filter_type, "trip")

    def test_passenger_vehicle_rejects_trip_service(self):
        with self.assertRaises(ValidationError):
            self._create_vehicle(
                "passenger",
                tms_service_product_id=self.trip_product.id,
                capacity=40,
            )

    def test_onchange_operation_clears_invalid_service(self):
        vehicle = self.env["fleet.vehicle"].new(
            {
                "name": "Vehicle cargo",
                "model_id": self.vehicle_model.id,
                "operation": "cargo",
                "tms_service_product_id": self.trip_product.id,
            }
        )
        vehicle.operation = "passenger"
        vehicle._onchange_operation_tms_service()
        self.assertFalse(vehicle.tms_service_product_id)
