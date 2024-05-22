# Copyright 2024 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_purchase_quantity_from_stock_move_line(self, po_line, move_lines):
        """Product on move line does not correspond with product on purchase line.

        Handle the quantity computation for specific cases (kits, ...)

        """
        qty = super()._get_purchase_quantity_from_stock_move_line(po_line, move_lines)
        if po_line.qty_received_method == "stock_moves" and po_line.move_ids.filtered(
            lambda m: m.state != "cancel"
        ):
            kit_bom = self.env["mrp.bom"]._bom_find(
                product=po_line.product_id,
                company_id=po_line.company_id.id,
                bom_type="phantom",
            )
            if kit_bom:
                moves = move_lines.move_id
                order_qty = po_line.product_uom._compute_quantity(
                    po_line.product_uom_qty, kit_bom.product_uom_id
                )
                filters = {
                    "incoming_moves": lambda m: m.location_id.usage == "supplier"
                    and (
                        not m.origin_returned_move_id
                        or (m.origin_returned_move_id and m.to_refund)
                    ),
                    "outgoing_moves": lambda m: m.location_id.usage != "supplier"
                    and m.to_refund,
                }
                qty = moves._compute_kit_quantities(
                    po_line.product_id, order_qty, kit_bom, filters
                )
        return qty
