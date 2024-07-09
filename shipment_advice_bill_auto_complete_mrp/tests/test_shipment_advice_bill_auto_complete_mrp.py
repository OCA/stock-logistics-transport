# Copyright 2024 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)
from odoo.tests.common import Form

from odoo.addons.shipment_advice.tests.common import Common


class TestCosanumAccountInvoiceAutoCompleteMrp(Common):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.supplier = cls.env.ref("base.res_partner_1")
        cls.kit_1 = cls.env.ref("mrp.product_product_table_kit")

        f = Form(cls.env["purchase.order"])
        f.partner_id = cls.supplier
        with f.order_line.new() as line:
            line.product_id = cls.kit_1
            line.product_qty = 5.0
            line.price_unit = 100
        cls.purchase = f.save()
        cls.purchase.button_confirm()

        cls.shipment = cls.shipment_advice_in

    @classmethod
    def _receive_goods(cls, pickings):
        for line in pickings.move_line_ids:
            line.qty_done = line.product_uom_qty
        pickings._action_done()

    def _get_vendor_bill_form(self):
        return Form(
            self.env["account.move"].with_context(default_move_type="in_invoice")
        )

    def test_select_shipment_with_one_supplier(self):
        """"""
        self.plan_records_in_shipment(self.shipment, self.purchase.picking_ids)
        self.progress_shipment_advice(self.shipment)
        self._receive_goods(self.purchase.picking_ids)
        self.shipment.action_done()
        # Invoice the shipment
        vendor_bill_form = self._get_vendor_bill_form()
        vendor_bill_form.shipment_advice_auto_complete_id = self.shipment
        vendor_bill = vendor_bill_form.save()
        # Supplier automatically selected
        self.assertEqual(vendor_bill.partner_id, self.purchase.partner_id)
        self.assertEqual(self.shipment.account_move_id, vendor_bill)
        invoice_line = vendor_bill.line_ids.filtered(
            lambda line: line.product_id == self.kit_1
        )
        # Fully revceived, fully invoiced
        self.assertEqual(invoice_line.quantity, 5.0)

    def test_select_shipment_with_goods_partially_received(self):
        pickings = self.purchase.picking_ids
        self.plan_records_in_shipment(self.shipment, pickings)
        self.progress_shipment_advice(self.shipment)
        # Partially receive the goods
        for line in pickings.move_line_ids:
            line.qty_done = line.product_uom_qty - 1
        wizard = (
            self.env["stock.backorder.confirmation"]
            .with_context(button_validate_picking_ids=pickings.ids)
            .create({"pick_ids": [(6, 0, pickings.ids)]})
        )
        wizard.process()
        self.shipment.action_done()
        # Invoice the shipment
        vendor_bill_form = self._get_vendor_bill_form()
        vendor_bill_form.shipment_advice_auto_complete_id = self.shipment
        vendor_bill = vendor_bill_form.save()
        self.assertEqual(vendor_bill.partner_id, self.purchase.partner_id)
        self.assertEqual(self.shipment.account_move_id, vendor_bill)
        invoice_line = vendor_bill.line_ids.filtered(
            lambda line: line.product_id == self.kit_1
        )
        self.assertEqual(invoice_line.quantity, 4.0)
