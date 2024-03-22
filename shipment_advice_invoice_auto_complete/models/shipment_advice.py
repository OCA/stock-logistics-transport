# Copyright 2024 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from collections import defaultdict

from odoo import api, fields, models
from odoo.tools import float_compare


class ShipmentAdvice(models.Model):
    _inherit = "shipment.advice"

    supplier_ids = fields.Many2many(
        comodel_name="res.partner",
        compute="_compute_supplier_ids",
        store=True,
        copy=False,
    )
    is_invoiced = fields.Boolean(compute="_compute_is_invoiced", store=True, copy=False)
    invoice_line_ids = fields.One2many(
        "account.move.line",
        "shipment_advice_id",
        string="Bill Lines",
        readonly=True,
        copy=False,
    )

    @api.depends("planned_move_ids.purchase_line_id.order_id.partner_id")
    def _compute_supplier_ids(self):
        for shipment in self:
            suppliers = False
            if shipment.shipment_type == "incoming":
                suppliers = (
                    shipment.planned_move_ids.purchase_line_id.order_id.partner_id
                )
            shipment.supplier_ids = suppliers

    def _get_invoiced_quantity_by_purchase_line(self):
        self.ensure_one()
        invoiced_quantities = defaultdict(int)
        for line in self.invoice_line_ids:
            if line.move_id.state == "cancel" or not line.purchase_line_id:
                continue
            quantity = line.product_uom_id._compute_quantity(
                line.quantity, line.product_id.uom_id
            )
            # No need to check the invoice type, the autocomplete is only enabled on in_invoice
            invoiced_quantities[line.purchase_line_id] += quantity
        return invoiced_quantities

    def _get_moves_quantity_done(self, moves):
        quantity_done = 0
        for move in moves:
            if move.state != "done":
                continue
            quantity_done += move.product_uom._compute_quantity(
                move.quantity_done, move.product_id.uom_id
            )
        return quantity_done

    def _get_invoicing_status(self):
        """Compute the invoicing status of an incoming shipment advice.

        Return True if it is fully invoiced, False otherwise.

        """
        self.ensure_one()
        if self.state != "done" or self.shipment_type != "incoming":
            return False
        purchase_line_invoicing = self._get_invoiced_quantity_by_purchase_line()
        purchase_line_invoiced = purchase_line_invoicing.keys()
        planned_moves = self.planned_move_ids
        for purchase_line, moves in planned_moves._group_by_purchase_line().items():
            if not purchase_line:
                continue
            if purchase_line not in purchase_line_invoiced:
                # Purchase line not invoiced yet
                return False
            invoiced_quantity = purchase_line_invoicing[purchase_line]
            quantity_done = self._get_moves_quantity_done(moves)
            uom_rounding = fields.first(moves.product_id.uom_id).rounding
            if float_compare(invoiced_quantity, quantity_done, uom_rounding) < 0:
                return False
        return True

    @api.depends("planned_move_ids", "invoice_line_ids")
    def _compute_is_invoiced(self):
        for shipment in self:
            shipment.is_invoiced = shipment._get_invoicing_status()
