# Copyright 2024 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models


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
            if shipment.shipment_type == "incoming":
                shipment.supplier_ids = (
                    shipment.planned_move_ids.purchase_line_id.order_id.partner_id
                )
            else:
                shipment.supplier_ids = False

    @api.depends("planned_move_ids", "invoice_line_ids")
    def _compute_is_invoiced(self):
        for shipment in self:
            if shipment.state != "done" or shipment.shipment_type != "incoming":
                shipment.is_invoiced = False
                continue
            # TODO: improve performance, maybe
            moves = shipment.planned_move_ids.filtered(
                lambda move: move.state == "done" and move.purchase_line_id
            )
            for move in moves:
                invoice_lines = shipment.invoice_line_ids.filtered(
                    lambda line: line.purchase_line_id == move.purchase_line_id
                    and line.move_id.state != "cancel"
                )
                if not sum(invoice_lines.mapped("quantity")) == move.quantity_done:
                    shipment.is_invoiced = False
                    break
            else:
                shipment.is_invoiced = True
