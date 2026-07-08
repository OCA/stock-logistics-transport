# Copyright (C) 2024 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models


class HrExpense(models.Model):
    _inherit = "hr.expense"

    @api.onchange("analytic_distribution", "trip_id")
    def _onchange_trip_id(self):
        if self.trip_id:
            self.analytic_distribution = self._default_analytic_distribution()

    def _default_analytic_distribution(self):
        trip = self.env.context.get("default_trip_id") or self.trip_id.id
        if not trip:
            return {}

        distribution = {}
        route_analytic_plan_group = self.env.ref(
            "tms_account.group_tms_route_analytic_plan"
        )
        order_analytic_plan_group = self.env.ref(
            "tms_account.group_tms_order_analytic_plan"
        )
        analytic_account_ids = []
        trip_id = self.env["tms.order"].browse(trip)

        if trip_id.route_id and route_analytic_plan_group:
            analytic_account_id = trip_id.route_id.analytic_account_id.id
            if analytic_account_id:
                analytic_account_ids.append(str(analytic_account_id))

        if order_analytic_plan_group:
            analytic_account_id = trip_id.analytic_account_id.id
            if analytic_account_id:
                analytic_account_ids.append(str(analytic_account_id))

        if analytic_account_ids:
            distribution[",".join(analytic_account_ids)] = 100

        self.analytic_distribution = distribution
        return distribution
