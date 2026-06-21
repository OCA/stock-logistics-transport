# Copyright (C) 2024 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models


class HrExpense(models.Model):
    _inherit = "hr.expense"

    trip_id = fields.Many2one("tms.order")

    def action_view_order(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "tms.order",
            "view_mode": "form",
            "res_id": self.trip_id.id,
            "target": "current",
            "name": _("Trip: %s") % self.trip_id.name,
        }
