# Copyright (C) 2024 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class TMSRoute(models.Model):
    _inherit = "tms.route"

    analytic_plan_id = fields.Many2one("account.analytic.plan")
    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        domain=[("plan_id", "=", "%(tms_account.tms_route_analytic_plan)d")],
        copy=False,
    )

    @api.model
    def create(self, vals_list):
        route = super().create(vals_list)
        if self.env.user.has_group("tms_account.group_tms_route_analytic_plan"):
            # If analytic account not provided
            if vals_list.get("analytic_account_id") in [False, None]:
                # Create analytic account
                analytic_plan = self.env.ref("tms_account.tms_route_analytic_plan")
                account_vals_list = {"name": route.name, "plan_id": analytic_plan.id}
                AccountAnalyticAccount = self.env["account.analytic.account"]
                account = AccountAnalyticAccount.create(account_vals_list)

                # Set the analytic_account_id
                route.analytic_account_id = account.id

        return route
