# Copyright 2024 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from collections import defaultdict

from odoo import _, api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    shipment_advice_auto_complete_id = fields.Many2one("shipment.advice", store=False)

    @api.onchange("shipment_advice_auto_complete_id")
    def _onchange_shipment_auto_complete(self):
        shipment = self.shipment_advice_auto_complete_id
        self.shipment_advice_auto_complete_id = False
        if (
            self.move_type not in ("in_invoice", "out_refund")
            or shipment.shipment_type != "incoming"
        ):
            return
        if not shipment.supplier_ids:
            return
        if len(shipment.supplier_ids) > 1:
            return {
                "warning": {
                    "title": _("Shipment with multiple suppliers"),
                    "message": _(
                        "There are multiple suppliers on the shipment advice."
                        "It can not be used to generate the vendor bill."
                    ),
                    "type": "notification",
                },
            }
        if self.partner_id and self.partner_id not in shipment.supplier_ids:
            return
        if not self.partner_id:
            self.partner_id = shipment.supplier_ids

        # Until the bill is saved, it is possible to select the same shipment multiple time
        # In this case remove all invoicing lines related to that shipment
        self.line_ids = self.line_ids.filtered(
            lambda line: line.shipment_advice_id != shipment
        )

        account_move_lines = self.env["account.move.line"]
        sequence = max(self.line_ids.mapped("sequence")) + 1 if self.line_ids else 10

        # FIXME should use the loaded_move_line_ids but does not
        #       seem to work at least with incoming shipment
        # move_lines = shipment.loaded_move_line_ids
        moves = shipment.planned_move_ids.filtered(
            lambda move: move.purchase_line_id.order_id.partner_id == self.partner_id
        )
        # Set currency
        if not self.currency_id:
            self.currency_id = fields.first(moves.purchase_line_id).currency_id
        move_lines = moves.move_line_ids.filtered(lambda line: line.state == "done")
        # Grouping by purchase line
        move_line_by_pol = defaultdict(lambda: self.env["stock.move.line"])
        for line in move_lines:
            move_line_by_pol[line.move_id.purchase_line_id] |= line
        for po_line, move_line in move_line_by_pol.items():
            if not po_line:
                continue
            quantity_done = self._get_purchase_quantity_from_stock_move_line(
                po_line, move_line
            )
            line_vals = po_line._prepare_account_move_line(self)
            line_vals.update(
                {
                    "sequence": sequence,
                    "shipment_advice_id": shipment.id,
                    "quantity": quantity_done,
                }
            )
            new_line = account_move_lines.new(line_vals)
            sequence += 1
            new_line.account_id = new_line._get_computed_account()
            new_line._onchange_price_subtotal()
            account_move_lines += new_line
        account_move_lines._onchange_mark_recompute_taxes()
        # Compute invoice_origin.
        origins = set(self.line_ids.mapped("purchase_line_id.order_id.name"))
        self.invoice_origin = ",".join(list(origins))
        # Compute ref.
        refs = self._get_invoice_reference()
        self.ref = ", ".join(refs)
        self._onchange_currency()
        return

    def _get_purchase_quantity_from_stock_move_line(self, po_line, move_lines):
        """Product on move line does not correspond with product on purchase line.

        Handle the quantity computation for specific cases (kits, ...)

        """
        quantity_done = 0
        if move_lines.product_id == po_line.product_id:
            quantity_done = sum(move_lines.mapped("qty_done"))
        return quantity_done

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        for move in moves:
            if move.move_type not in ("in_invoice", "out_refund"):
                continue
            shipment = move.line_ids.mapped("shipment_advice_id")
            if not shipment:
                continue
            refs = [
                "<a href=# data-oe-model=shipment.advice data-oe-id=%s>%s</a>"
                % tuple(name_get)
                for name_get in shipment.name_get()
            ]
            message = _("This vendor bill has been created from: %s") % ",".join(refs)
            move.message_post(body=message)
        return moves

    def write(self, vals):
        old_shipment = {
            move.id: move.mapped("line_ids.shipment_advice_id") for move in self
        }
        res = super().write(vals)
        for move in self:
            if move.move_type not in ("in_invoice", "out_refund"):
                continue
            new_shipment = move.mapped("line_ids.shipment_advice_id")
            if not new_shipment:
                continue
            diff_shipments = new_shipment - old_shipment[move.id]
            if diff_shipments:
                refs = [
                    "<a href=# data-oe-model=shipment.advice data-oe-id=%s>%s</a>"
                    % tuple(name_get)
                    for name_get in diff_shipments.name_get()
                ]
                message = _("This vendor bill has been modified from: %s") % ",".join(
                    refs
                )
                move.message_post(body=message)
        return res
