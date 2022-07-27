from datetime import timedelta

from odoo import fields

from odoo.addons.purchase_stock.tests.common import PurchaseTestCommon


class TestPurchaseBuyRule(PurchaseTestCommon):
    def test_no_destination(self):
        company = self.env.ref("base.main_company")
        # Update company with Purchase Lead Time
        company.write({"po_lead": 3.00})
        date_planned = fields.Datetime.now() + timedelta(days=10)
        # Prepare string from timestamp
        date_planned_str = fields.Datetime.to_string(date_planned)
        # This function takes a date as argument
        self._create_make_procurement(self.product_1, 15.00, date_planned=date_planned)
        purchase = (
            self.env["purchase.order.line"]
            .search([("product_id", "=", self.product_1.id)], limit=1)
            .order_id
        )
        self.assertTrue(purchase)
        self.assertFalse(purchase.dest_address_id)
        # Test for TypeError when passing date as string
        self.assertRaises(
            TypeError,
            self._create_make_procurement(
                self.product_1, 15.00, date_planned=date_planned_str
            ),
        )

    def test_destination(self):
        company = self.env.ref("base.main_company")
        # Update company with Purchase Lead Time
        company.write({"po_lead": 3.00})
        date_planned = fields.Datetime.now() + timedelta(days=10)
        date_planned_str = fields.Datetime.to_string(date_planned)
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
        self.assertRaises(
            TypeError,
            self._create_make_procurement(
                self.product_1, 15.00, date_planned=date_planned_str
            ),
        )
