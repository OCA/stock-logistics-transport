# Copyright (C) 2026 VSL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class TmsDriver(models.Model):
    _inherit = "tms.driver"

    def action_view_sale_orders(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "sale.act_res_partner_2_sale_order"
        )
        action["context"] = {"default_partner_id": self.partner_id.id}
        action["domain"] = [("partner_id", "child_of", self.partner_id.id)]
        return action
