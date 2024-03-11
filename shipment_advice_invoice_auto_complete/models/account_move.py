# Copyright 2024 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import _, api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    shipment_vendor_bill_id = fields.Many2one("shipment.advice", store=False)

    @api.onchange("shipment_vendor_bill_id")
    def _onchange_shipment_auto_complete(self):
        shipment = self.shipment_vendor_bill_id
        self.shipment_vendor_bill_id = False
        if not shipment.shipment_type == "incoming":
            return
        if not shipment.supplier_ids:
            return
        if not self.partner_id:
            if len(shipment.supplier_ids) > 1:
                return {
                    "warning": {
                        "title": _("Select a supplier first"),
                        "message": _(
                            "There is multiple suppliers on the shipment advice."
                            "Please, first select a supplier for the vendor bill."
                        ),
                        "type": "notification",
                    },
                }
            else:
                self.partner_id = shipment.supplier_ids
                self._onchange_partner_id()
        elif self.partner_id not in shipment.supplier_ids:
            return

        new_lines = self.env["account.move.line"]
        moves = shipment.planned_move_ids
        moves = moves.filtered(
            lambda move: move.state == "done"
            and move.purchase_line_id.order_id.partner_id == self.partner_id
        )
        sequence = max(self.line_ids.mapped("sequence")) + 1 if self.line_ids else 10
        for move in moves:
            if not move.purchase_line_id:
                continue
            line = move.purchase_line_id
            line_vals = line._prepare_account_move_line(self)
            if line_vals.get("quantity") == 0:
                # Already fully invoiced
                continue
            line_vals.update(
                {
                    "sequence": sequence,
                    "shipment_advice_id": shipment.id,
                    # Only invoice what was delivered by the move
                    "quantity": move.product_qty,
                }
            )
            new_line = new_lines.new(line_vals)
            sequence += 1
            new_line.account_id = new_line._get_computed_account()
            new_line._onchange_price_subtotal()
            new_lines += new_line
        new_lines._onchange_mark_recompute_taxes()
        self._onchange_currency()
        return
