# Copyright (C) 2024 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    has_tms_order = fields.Boolean(readonly=True, compute="_compute_has_trip")

    @api.depends("line_ids")
    def _compute_has_trip(self):
        for record in self:
            if record.line_ids.sale_line_ids.order_id.tms_order_ids:
                record.has_tms_order = True
            else:
                record.has_tms_order = False

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
