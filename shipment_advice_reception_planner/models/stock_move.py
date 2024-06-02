# Copyright 2024 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockMove(models.Model):
    _inherit = "stock.move"

    origin_purchase = fields.Char(
        compute="_compute_origin_purchase", search="_search_origin_purchase"
    )
    quantity_to_split_wizard = fields.Float(
        string="Receiving Qty",
        store=False,
        readonly=False,
        default=lambda self: self.product_uom_qty,
    )

    @api.depends("purchase_line_id")
    def _compute_origin_purchase(self):
        for move in self:
            if not move.purchase_line_id:
                move.origin_purchase = False
                continue
            purchase = move.purchase_line_id.order_id
            if purchase.name and purchase.origin:
                move.origin_purchase = f"{purchase.name} {purchase.origin}"
            else:
                move.origin_purchase = purchase.name or purchase.origin

    def _search_origin_purchase(self, operator, value):
        purchases = self.env["purchase.order"].search(
            ["|", ("name", operator, value), ("origin", operator, value)]
        )
        return [("purchase_line_id", "in", purchases.order_line.ids)]

    @api.onchange("quantity_to_split_wizard")
    def _onchange_quantity_to_split(self):
        if (
            self.quantity_to_split_wizard <= 0
            or self.quantity_to_split_wizard > self.product_uom_qty
        ):
            raise UserError(
                _(
                    "The receiving quantity must be more than zero but not more than the demand"
                )
            )
