# Copyright (C) 2024 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        route_plan = self.env.ref(
            "tms_account.tms_route_analytic_plan", raise_if_not_found=False
        ).sudo()
        order_plan = self.env.ref(
            "tms_account.tms_order_analytic_plan", raise_if_not_found=False
        ).sudo()
        for line, vals in zip(lines, vals_list, strict=True):
            sudo_line = line.sudo()
            amount = sudo_line.amount
            if route_plan:
                route_column = route_plan._column_name()
                if route_column in vals and vals[route_column]:
                    account = sudo_line[route_column]
                    for route in account.route_id:
                        if amount < 0:
                            route.total_expenses += abs(amount)
                        else:
                            route.total_income += amount
            if order_plan:
                order_column = order_plan._column_name()
                if order_column in vals and vals[order_column]:
                    account = sudo_line[order_column]
                    for trip in account.trip_id:
                        if amount < 0:
                            trip.total_expenses += abs(amount)
                        else:
                            trip.total_income += amount
        return lines
