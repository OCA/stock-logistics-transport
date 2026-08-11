# Copyright (C) 2026 VSL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class TmsDriver(models.Model):
    _inherit = "tms.driver"

    def action_view_purchase_orders(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "purchase.act_res_partner_2_purchase_order"
        )
        action["context"] = {
            "search_default_partner_id": self.partner_id.id,
            "default_partner_id": self.partner_id.id,
        }
        return action
