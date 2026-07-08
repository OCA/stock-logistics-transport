# Copyright (C) 2024 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    has_tms_order = fields.Boolean(readonly=True, compute="_compute_has_trip")

    @api.depends("line_ids")
    def _compute_has_trip(self):
        for record in self:
            record.has_tms_order = bool(
                record.line_ids.sale_line_ids.order_id.tms_order_ids
            )

    def _prepare_product_base_line_for_taxes_computation(self, product_line):
        base_line = super()._prepare_product_base_line_for_taxes_computation(
            product_line
        )
        tms_factor = product_line.tms_factor or 1.0
        if tms_factor != 1.0 and self.is_invoice(include_receipts=True):
            base_line["quantity"] = base_line.get("quantity", 1.0) * tms_factor
        return base_line

    def action_view_tms_orders(self):
        self.ensure_one()
        tms_orders = self.line_ids.sale_line_ids.order_id.tms_order_ids
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "tms.action_tms_dash_order"
        )
        if len(tms_orders) > 1:
            action["domain"] = [("id", "in", tms_orders.ids)]
        else:
            action["views"] = [(self.env.ref("tms.tms_order_view_form").id, "form")]
            action["res_id"] = tms_orders.id

        return action
