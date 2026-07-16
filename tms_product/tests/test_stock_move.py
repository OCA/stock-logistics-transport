# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError

from odoo.addons.base.tests.common import BaseCommon


class TestStockMove(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.vehicle_model = cls.env["fleet.vehicle.model"].create(
            {
                "name": "Move Model",
                "brand_id": cls.env["fleet.vehicle.model.brand"]
                .create({"name": "Move Brand"})
                .id,
                "vehicle_type": "car",
            }
        )
        cls.vehicle_product = cls.env["product.product"].create(
            {
                "name": "Vehicle Product",
                "type": "consu",
                "tracking": "serial",
                "tms_vehicle": True,
                "vehicle_type": "car",
                "model_id": cls.vehicle_model.id,
            }
        )
        cls.picking_type_in = cls.env.ref("stock.picking_type_in")
        cls.supplier_location = cls.env.ref("stock.stock_location_suppliers")
        cls.stock_location = cls.env.ref("stock.stock_location_stock")

    def _create_incoming_picking(self, product, qty=1.0):
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.picking_type_in.id,
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
            }
        )
        self.env["stock.move"].create(
            {
                "product_id": product.id,
                "product_uom": product.uom_id.id,
                "product_uom_qty": qty,
                "picking_id": picking.id,
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
            }
        )
        return picking

    def test_prepare_vehicle_values(self):
        lot = self.env["stock.lot"].create(
            {
                "name": "SN-MOVE-1",
                "product_id": self.vehicle_product.id,
            }
        )
        picking = self._create_incoming_picking(self.vehicle_product)
        move = picking.move_ids
        move_line = self.env["stock.move.line"].create(
            {
                "move_id": move.id,
                "product_id": self.vehicle_product.id,
                "product_uom_id": self.vehicle_product.uom_id.id,
                "quantity": 1.0,
                "lot_id": lot.id,
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
            }
        )
        vals = move._prepare_vehicle_values(move_line)
        self.assertEqual(vals["model_id"], self.vehicle_model.id)
        self.assertEqual(vals["product_id"], self.vehicle_product.id)
        self.assertEqual(vals["lot_id"], lot.id)
        self.assertEqual(vals["stock_picking_id"], picking.id)

    def test_vehicle_creation_on_receipt_validation(self):
        lot = self.env["stock.lot"].create(
            {
                "name": "SN-MOVE-2",
                "product_id": self.vehicle_product.id,
            }
        )
        picking = self._create_incoming_picking(self.vehicle_product)
        move = picking.move_ids
        self.env["stock.move.line"].create(
            {
                "move_id": move.id,
                "product_id": self.vehicle_product.id,
                "product_uom_id": self.vehicle_product.uom_id.id,
                "quantity": 1.0,
                "lot_id": lot.id,
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
            }
        )
        picking.button_validate()
        self.assertTrue(lot.vehicle_id)
        self.assertEqual(lot.vehicle_id.stock_picking_id, picking)

    def test_non_vehicle_receipt_completes(self):
        product = self.env["product.product"].create(
            {
                "name": "Regular Product",
                "type": "consu",
                "tracking": "serial",
            }
        )
        lot = self.env["stock.lot"].create(
            {
                "name": "SN-MOVE-4",
                "product_id": product.id,
            }
        )
        picking = self._create_incoming_picking(product)
        move = picking.move_ids
        self.env["stock.move.line"].create(
            {
                "move_id": move.id,
                "product_id": product.id,
                "product_uom_id": product.uom_id.id,
                "quantity": 1.0,
                "lot_id": lot.id,
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
            }
        )
        picking.button_validate()
        self.assertFalse(lot.vehicle_id)

    def test_missing_model_raises_user_error(self):
        product = self.env["product.product"].create(
            {
                "name": "Vehicle Without Model",
                "type": "consu",
                "tracking": "serial",
                "tms_vehicle": True,
                "vehicle_type": "car",
            }
        )
        lot = self.env["stock.lot"].create(
            {
                "name": "SN-MOVE-3",
                "product_id": product.id,
            }
        )
        picking = self._create_incoming_picking(product)
        move = picking.move_ids
        self.env["stock.move.line"].create(
            {
                "move_id": move.id,
                "product_id": product.id,
                "product_uom_id": product.uom_id.id,
                "quantity": 1.0,
                "lot_id": lot.id,
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
            }
        )
        with self.assertRaises(UserError):
            picking.button_validate()
