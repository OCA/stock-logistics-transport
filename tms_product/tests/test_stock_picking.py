# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.base.tests.common import BaseCommon


class TestStockPicking(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.vehicle_model = cls.env["fleet.vehicle.model"].create(
            {
                "name": "Picking Model",
                "brand_id": cls.env["fleet.vehicle.model.brand"]
                .create({"name": "Picking Brand"})
                .id,
            }
        )
        cls.picking = cls.env["stock.picking"].create(
            {
                "picking_type_id": cls.env.ref("stock.picking_type_in").id,
                "location_id": cls.env.ref("stock.stock_location_suppliers").id,
                "location_dest_id": cls.env.ref("stock.stock_location_stock").id,
            }
        )

    def test_tms_vehicle_count(self):
        self.assertEqual(self.picking.tms_vehicle_count, 0)
        self.env["fleet.vehicle"].create(
            {
                "name": "Linked Vehicle",
                "model_id": self.vehicle_model.id,
                "stock_picking_id": self.picking.id,
            }
        )
        self.assertEqual(self.picking.tms_vehicle_count, 1)

    def test_action_view_tms_vehicle(self):
        vehicle = self.env["fleet.vehicle"].create(
            {
                "name": "Linked Vehicle",
                "model_id": self.vehicle_model.id,
                "stock_picking_id": self.picking.id,
            }
        )
        action = self.picking.action_view_tms_vehicle()
        self.assertEqual(action["res_model"], "fleet.vehicle")
        self.assertIn(vehicle.id, action["domain"][0][2])
