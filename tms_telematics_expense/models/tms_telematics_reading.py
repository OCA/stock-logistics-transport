# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class TmsTelematicsReading(models.Model):
    _inherit = "tms.telematics.reading"

    fuel_cost = fields.Float(string="Fuel cost", digits="Product Price", copy=False)
    expense_id = fields.Many2one(
        "hr.expense",
        string="Expense",
        copy=False,
        index=True,
        ondelete="set null",
    )

    def action_open_expense(self):
        self.ensure_one()
        if not self.expense_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Expense"),
            "res_model": "hr.expense",
            "view_mode": "form",
            "res_id": self.expense_id.id,
        }
