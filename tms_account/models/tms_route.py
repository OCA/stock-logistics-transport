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
    total_revenue = fields.Float(
        default=0,
        readonly=True,
        compute="_compute_total_revenue",
        store=True,
        groups="analytic.group_analytic_accounting",
    )
    total_expenses = fields.Float(
        default=0, readonly=True, groups="analytic.group_analytic_accounting"
    )
    total_income = fields.Float(
        default=0, readonly=True, groups="analytic.group_analytic_accounting"
    )

    @api.depends("total_expenses", "total_income")
    def _compute_total_revenue(self):
        for record in self:
            record.total_revenue = record.total_income - record.total_expenses

    @api.model_create_multi
    def create(self, vals_list):
        routes = super().create(vals_list)
        if not self.env.user.has_group("tms_account.group_tms_route_analytic_plan"):
            return routes
        analytic_plan = self.env.ref("tms_account.tms_route_analytic_plan")
        AccountAnalyticAccount = self.env["account.analytic.account"]
        for route, vals in zip(routes, vals_list, strict=True):
            if vals.get("analytic_account_id"):
                continue
            account = AccountAnalyticAccount.create(
                {"name": route.name, "plan_id": analytic_plan.id}
            )
            route.analytic_account_id = account
        return routes
