# Copyright (C) 2024 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    @api.model
    def create(self, vals):
        line = super().create(vals)
        if "x_plan3_id" in vals:
            amount = line.amount
            if amount < 0:
                line.x_plan3_id.trip_id.total_expenses += abs(amount)
            else:
                line.x_plan3_id.trip_id.total_income += amount
        if "x_plan2_id" in vals:
            amount = line.amount
            if amount < 0:
                line.x_plan2_id.route_id.total_expenses += abs(amount)
            else:
                line.x_plan2_id.route_id.total_income += amount
        return line
