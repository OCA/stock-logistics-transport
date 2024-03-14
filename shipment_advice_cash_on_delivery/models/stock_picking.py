# Copyright 2018 Jacques-Etienne Baudoux (BCIM) <je@bcim.be>
# Copyright 2023 ACSONE SA/NV
# Copyright 2024 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    cash_on_delivery_invoice_ids = fields.Many2many(
        "account.move", string="COD Invoices", copy=False, readonly=True
    )

    def _invoice_at_shipping(self):
        self.ensure_one()
        res = super()._invoice_at_shipping()
        res = res or self.sale_id.payment_term_id.cash_on_delivery
        return res

    def _invoicing_at_shipping_validation(self, invoices):
        # COD invoices (with partner who doesn't have auto_validate_invoice)
        # will be not validated automatically
        invoices_to_validate = invoices.filtered(
            lambda invoice: not invoice.invoice_payment_term_id.cash_on_delivery
            or invoice.partner_id.auto_validate_invoice
        )
        res = super()._invoicing_at_shipping_validation(invoices_to_validate)
        return res

    def _invoicing_at_shipping(self):
        self.ensure_one()
        res = super()._invoicing_at_shipping()
        if not isinstance(res, str):
            cod_invoices = res.filtered(
                lambda inv: inv.invoice_payment_term_id.cash_on_delivery
            )
            self.cash_on_delivery_invoice_ids = cod_invoices
        return res
