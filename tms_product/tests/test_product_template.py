# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.base.tests.common import BaseCommon


class TestProductTemplate(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.vehicle_model = cls.env["fleet.vehicle.model"].create(
            {
                "name": "Test Model",
                "brand_id": cls.env["fleet.vehicle.model.brand"]
                .create({"name": "Test Brand"})
                .id,
                "vehicle_type": "car",
            }
        )

    def test_service_product_clears_tms_vehicle(self):
        product = self.env["product.template"].create(
            {
                "name": "Trip Service",
                "type": "consu",
                "tms_vehicle": True,
            }
        )
        product.type = "service"
        self.assertFalse(product.tms_vehicle)

    def test_goods_product_clears_tms_trip(self):
        product = self.env["product.template"].create(
            {
                "name": "Vehicle Product",
                "type": "service",
                "tms_trip": True,
            }
        )
        product.type = "consu"
        self.assertFalse(product.tms_trip)

    def test_trip_fields_cleared_when_not_trip(self):
        product = self.env["product.template"].create(
            {
                "name": "Trip Service",
                "type": "service",
                "tms_trip": True,
                "trip_product_type": "trip",
                "tms_factor_type": "distance",
                "tms_factor_distance_uom": self.env.ref("uom.product_uom_meter").id,
            }
        )
        product.tms_trip = False
        self.assertFalse(product.trip_product_type)
        self.assertFalse(product.tms_factor_type)
        self.assertFalse(product.tms_factor_distance_uom)

    def test_vehicle_type_selection(self):
        selection = self.env["product.template"]._compute_vehicle_type_selection()
        fleet_selection = self.env["fleet.vehicle.model"].fields_get(["vehicle_type"])[
            "vehicle_type"
        ]["selection"]
        self.assertEqual(selection, fleet_selection)

    def test_vehicle_fields_on_template(self):
        product = self.env["product.template"].create(
            {
                "name": "Vehicle Product",
                "type": "consu",
                "tms_vehicle": True,
                "vehicle_type": "car",
                "model_id": self.vehicle_model.id,
            }
        )
        self.assertTrue(product.tms_vehicle)
        self.assertEqual(product.vehicle_type, "car")
        self.assertEqual(product.model_id, self.vehicle_model)

    def test_vehicle_fields_cleared_when_not_trip_product(self):
        product = self.env["product.template"].create(
            {
                "name": "Vehicle Product",
                "type": "consu",
                "tms_vehicle": True,
                "vehicle_type": "car",
                "model_id": self.vehicle_model.id,
                "tms_trip": False,
            }
        )
        product._compute_restore_vehicle_fields()
        self.assertFalse(product.vehicle_type)
        self.assertFalse(product.model_id)
