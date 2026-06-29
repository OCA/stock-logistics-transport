# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.base.tests.common import BaseCommon


class TestStockLot(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.product = cls.env["product.product"].create(
            {
                "name": "Tracked Vehicle Product",
                "type": "consu",
                "tracking": "serial",
            }
        )
        cls.lot = cls.env["stock.lot"].create(
            {
                "name": "SN001",
                "product_id": cls.product.id,
            }
        )
        cls.vehicle_model = cls.env["fleet.vehicle.model"].create(
            {
                "name": "Lot Model",
                "brand_id": cls.env["fleet.vehicle.model.brand"]
                .create({"name": "Lot Brand"})
                .id,
            }
        )
        cls.vehicle = cls.env["fleet.vehicle"].create(
            {
                "name": "Lot Vehicle",
                "model_id": cls.vehicle_model.id,
            }
        )
        cls.lot.vehicle_id = cls.vehicle

    def test_action_view_vehicle(self):
        action = self.lot.action_view_vehicle()
        self.assertEqual(action["res_model"], "fleet.vehicle")
        self.assertEqual(action["res_id"], self.vehicle.id)
        self.assertIn("SN001", action["name"])
