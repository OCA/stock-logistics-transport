# Copyright 2018 Creu Blanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import Command, fields

from odoo.addons.base.tests.common import BaseCommon


class TestPickingAddress(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].create(
            {"name": "Test Warehouse", "code": "TEST_WH"}
        )
        cls.sequence = cls.env["ir.sequence"].create(
            {"name": "Picking test sequence", "company_id": False}
        )
        cls.partner = cls.env["res.partner"].create({"name": "Partner"})
        cls.location_partner = cls.env["res.partner"].create(
            {"name": "Location_address"}
        )
        cls.location = cls.env["stock.location"].create(
            {
                "name": "Location",
                "location_id": cls.warehouse.view_location_id.id,
                "usage": "internal",
                "address_id": cls.location_partner.id,
            }
        )
        cls.picking_01 = cls.env["stock.picking.type"].create(
            {
                "code": "incoming",
                "name": "Picking 01",
                "sequence_id": cls.sequence.id,
                "sequence_code": "IN",
                "warehouse_id": cls.warehouse.id,
                "default_location_dest_id": cls.location.id,
            }
        )
        cls.picking_02 = cls.env["stock.picking.type"].create(
            {
                "code": "incoming",
                "name": "Picking 02",
                "sequence_id": cls.sequence.id,
                "sequence_code": "IN",
                "warehouse_id": cls.warehouse.id,
                "default_location_dest_id": cls.warehouse.lot_stock_id.id,
            }
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Product", "type": "product", "purchase_ok": True}
        )

    def test_onchange_purchase(self):
        purchase = self.env["purchase.order"].new(
            {"partner_id": self.partner.id, "picking_type_id": self.picking_01.id}
        )
        self.assertEqual(self.location_partner, purchase.dest_address_id)
        purchase.update({"picking_type_id": self.picking_02.id})
        self.assertFalse(purchase.dest_address_id)

    def test_purchase_with_destination(self):
        purchase = self.env["purchase.order"].create(
            {
                "partner_id": self.partner.id,
                "picking_type_id": self.picking_01.id,
                "order_line": [
                    Command.create(
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
        self.assertEqual(self.location.address_id, purchase.dest_address_id)
        purchase.button_confirm()
        self.assertEqual(purchase.picking_ids.location_dest_id, self.location)

    def test_purchase_without_destination(self):
        purchase = self.env["purchase.order"].create(
            {
                "partner_id": self.partner.id,
                "picking_type_id": self.picking_02.id,
                "order_line": [
                    Command.create(
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
        purchase.button_confirm()
        self.assertFalse(purchase.dest_address_id)
