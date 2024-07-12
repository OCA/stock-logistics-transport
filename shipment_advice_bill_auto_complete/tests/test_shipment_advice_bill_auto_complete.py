# Copyright 2024 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)
from odoo.tests.common import Form

from odoo.addons.shipment_advice.tests.common import Common


class TestShipmentAdviceBillAutoComplete(Common):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.product_1 = cls.env.ref("product.product_product_25")
        cls.product_2 = cls.env.ref("product.product_product_20")
        cls.order = cls.env.ref("purchase.purchase_order_1")
        cls.supplier_1 = cls.env.ref("base.res_partner_1")
        cls.supplier_2 = cls.env.ref("base.res_partner_2")
        cls.supplier = cls.order.partner_id
        cls.invoice = cls.env["account.move"].create(
            {"partner_id": cls.supplier.id, "move_type": "in_invoice"}
        )
        cls.order.button_confirm()
        cls.shipment = cls.shipment_advice_in

        cls.purchase_1 = cls._create_purchase_order(
            cls.supplier_1, [(cls.product_1, 5), (cls.product_2, 12)]
        )
        cls.purchase_2 = cls._create_purchase_order(
            cls.supplier_2, [(cls.product_1, 3), (cls.product_2, 13)]
        )

    @classmethod
    def _create_purchase_order(cls, partner, products):
        po = cls.env["purchase.order"].create(
            {
                "partner_id": partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "name": "TEST",
                            "product_id": product.id,
                            "product_qty": qty,
                            "product_uom": product.uom_id.id,
                            "price_unit": 3,
                        },
                    )
                    for product, qty in products
                ],
            }
        )
        po.button_confirm()
        return po

    @classmethod
    def _receive_goods(cls, pickings):
        for line in pickings.move_line_ids:
            line.qty_done = line.product_uom_qty
        pickings._action_done()

    def _get_vendor_bill_form(self):
        return Form(
            self.env["account.move"].with_context(default_move_type="in_invoice")
        )

    def _check_invoiced_lines(self, invoice, pickings):
        """Check invoice lines are correctcly created from shipment moves."""
        invoice_lines = invoice.line_ids.filtered(lambda line: line.shipment_advice_id)
        moves = pickings.move_lines.filtered(lambda move: move.state == "done")
        self.assertEqual(len(invoice_lines), len(moves))
        for move in moves:
            invoice_line = invoice_lines.filtered(
                lambda l: l.purchase_line_id == move.purchase_line_id
            )
            self.assertEqual(invoice_line.product_id, move.product_id)
            self.assertEqual(invoice_line.quantity, move.product_qty)
            self.assertEqual(invoice_line.shipment_advice_id, move.shipment_advice_id)

    def test_select_shipment_with_different_supplier(self):
        """Check shipment selected has not the same supplier than the invoice."""
        self.plan_records_in_shipment(self.shipment, self.purchase_1.picking_ids)
        self.progress_shipment_advice(self.shipment)
        self._receive_goods(self.purchase_1.picking_ids)
        self.shipment.action_done()
        # Invoice the shipment
        vendor_bill = self._get_vendor_bill_form()
        vendor_bill.partner_id = self.purchase_2.partner_id
        vendor_bill.shipment_advice_auto_complete_id = self.shipment
        invoice = vendor_bill.save()
        # Supplier on vendor bill has not changed
        self.assertEqual(invoice.partner_id, self.purchase_2.partner_id)
        self.assertFalse(invoice.line_ids)

    def test_select_shipment_with_one_supplier(self):
        """Check invoicing shipment with one supplier."""
        self.plan_records_in_shipment(self.shipment, self.purchase_1.picking_ids)
        self.progress_shipment_advice(self.shipment)
        self._receive_goods(self.purchase_1.picking_ids)
        self.shipment.action_done()
        # Invoice the shipment
        vendor_bill = self._get_vendor_bill_form()
        vendor_bill.shipment_advice_auto_complete_id = self.shipment
        invoice = vendor_bill.save()
        # Supplier automatically selected
        self.assertEqual(invoice.partner_id, self.purchase_1.partner_id)
        self._check_invoiced_lines(invoice, self.purchase_1.picking_ids)
        self.assertEqual(self.shipment.account_move_id, invoice)

    def test_select_shipment_with_goods_partially_received(self):
        pickings = self.purchase_1.picking_ids
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
        vendor_bill = self._get_vendor_bill_form()
        vendor_bill.shipment_advice_auto_complete_id = self.shipment
        invoice = vendor_bill.save()
        self._check_invoiced_lines(invoice, pickings)
