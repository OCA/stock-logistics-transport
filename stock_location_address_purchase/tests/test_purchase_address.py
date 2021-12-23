# Copyright 2018 Creu Blanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields
from odoo.tests import TransactionCase


class TestPickingAddress(TransactionCase):
    def setUp(self):
        super().setUp()
        self.warehouse = self.env["stock.warehouse"].create(
            {"name": "Test Warehouse", "code": "TEST_WH"}
        )
        self.sequence = self.env["ir.sequence"].create(
            {"name": "Picking test sequence", "company_id": False}
        )
        self.partner = self.env["res.partner"].create({"name": "Partner"})
        self.location_partner = self.env["res.partner"].create(
            {"name": "Location_address"}
        )
        self.location = self.env["stock.location"].create(
            {
                "name": "Location",
                "location_id": self.warehouse.view_location_id.id,
                "usage": "internal",
                "address_id": self.location_partner.id,
            }
        )
        self.picking_01 = self.env["stock.picking.type"].create(
            {
                "code": "incoming",
                "name": "Picking 01",
                "sequence_id": self.sequence.id,
                "sequence_code": "IN",
                "warehouse_id": self.warehouse.id,
                "default_location_dest_id": self.location.id,
            }
        )
        self.picking_02 = self.env["stock.picking.type"].create(
            {
                "code": "incoming",
                "name": "Picking 02",
                "sequence_id": self.sequence.id,
                "sequence_code": "IN",
                "warehouse_id": self.warehouse.id,
                "default_location_dest_id": self.warehouse.lot_stock_id.id,
            }
        )
        self.product = self.env["product.product"].create(
            {"name": "Product", "type": "product", "purchase_ok": True}
        )

    def test_onchange_purchase(self):
        purchase = self.env["purchase.order"].new(
            {"partner_id": self.partner.id, "picking_type_id": self.picking_01.id}
        )
        purchase._onchange_picking_type_id()
        self.assertEqual(self.location_partner, purchase.dest_address_id)
        purchase.update({"picking_type_id": self.picking_02.id})
        purchase._onchange_picking_type_id()
        self.assertFalse(purchase.dest_address_id)

    def test_purchase_with_destination(self):
        purchase = self.env["purchase.order"].create(
            {
                "partner_id": self.partner.id,
                "picking_type_id": self.picking_01.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_qty": 1,
                            "name": self.product.name,
                            "date_planned": fields.Date.today(),
                            "product_uom": self.product.uom_po_id.id,
                            "price_unit": 1,
                        },
                    )
                ],
            }
        )
        purchase._onchange_picking_type_id()
        self.assertEqual(self.location.address_id, purchase.dest_address_id)
        purchase.button_confirm()
        self.assertEqual(purchase.picking_ids.location_dest_id, self.location)

    def test_purchase_without_destination(self):
        purchase = self.env["purchase.order"].create(
            {
                "partner_id": self.partner.id,
                "picking_type_id": self.picking_02.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "name": self.product.name,
                            "date_planned": fields.Date.today(),
                            "product_qty": 1,
                            "product_uom": self.product.uom_po_id.id,
                            "price_unit": 1,
                        },
                    )
                ],
            }
        )
        purchase._onchange_picking_type_id()
        purchase.button_confirm()
        self.assertFalse(purchase.dest_address_id)
