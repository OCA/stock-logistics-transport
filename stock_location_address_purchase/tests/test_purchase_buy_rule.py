from datetime import timedelta

from odoo import fields

from odoo.addons.purchase_stock.tests.common import PurchaseTestCommon


class TestPurchaseBuyRule(PurchaseTestCommon):
    def test_no_destination(self):
        company = self.env.ref("base.main_company")
        # Update company with Purchase Lead Time
        company.write({"po_lead": 3.00})
        date_planned = fields.Datetime.to_string(
            fields.datetime.now() + timedelta(days=10)
        )
        self._create_make_procurement(self.product_1, 15.00, date_planned=date_planned)
        purchase = (
            self.env["purchase.order.line"]
            .search([("product_id", "=", self.product_1.id)], limit=1)
            .order_id
        )
        self.assertTrue(purchase)
        self.assertFalse(purchase.dest_address_id)

    def test_destination(self):
        company = self.env.ref("base.main_company")
        # Update company with Purchase Lead Time
        company.write({"po_lead": 3.00})
        date_planned = fields.Datetime.to_string(
            fields.datetime.now() + timedelta(days=10)
        )
        partner = self.env["res.partner"].create({"name": "DEMO Partner"})
        self.warehouse_1.lot_stock_id.real_address_id = partner
        self._create_make_procurement(self.product_1, 15.00, date_planned=date_planned)
        purchase = (
            self.env["purchase.order.line"]
            .search([("product_id", "=", self.product_1.id)], limit=1)
            .order_id
        )
        self.assertTrue(purchase)
        self.assertTrue(purchase.dest_address_id)
        self.assertEqual(purchase.dest_address_id, partner)
