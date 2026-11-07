# Copyright (C) 2024 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models


class HrExpense(models.Model):
    _inherit = "hr.expense"

    @api.onchange("analytic_distribution", "trip_id")
    def _onchange_trip_id(self):
        if self.trip_id or self.allocation_ids:
            self.analytic_distribution = self._default_analytic_distribution()

    def _default_analytic_distribution(self):
        if self.product_id.tms_spread_by_distance:
            distribution = self._distribution_from_allocations()
        else:
            distribution = self._distribution_for_single_trip()
        self.analytic_distribution = distribution
        return distribution

    def _analytic_accounts_for_trip(self, trip):
        accounts = []
        route_group = self.env.ref("tms_account.group_tms_route_analytic_plan")
        order_group = self.env.ref("tms_account.group_tms_order_analytic_plan")
        if trip.route_id and route_group and trip.route_id.analytic_account_id:
            accounts.append(str(trip.route_id.analytic_account_id.id))
        if order_group and trip.analytic_account_id:
            accounts.append(str(trip.analytic_account_id.id))
        return accounts

    def _distribution_for_single_trip(self):
        trip = self.env.context.get("default_trip_id") or self.trip_id.id
        if not trip:
            return {}
        trip_id = self.env["tms.order"].browse(trip)
        analytic_account_ids = self._analytic_accounts_for_trip(trip_id)
        if not analytic_account_ids:
            return {}
        return {",".join(analytic_account_ids): 100}

    def _distribution_from_allocations(self):
        total = self.total_amount
        if not total:
            return {}
        distribution = {}
        for line in self.allocation_ids:
            accounts = self._analytic_accounts_for_trip(line.trip_id)
            if not accounts:
                continue
            key = ",".join(accounts)
            share = (line.amount / total) * 100
            distribution[key] = distribution.get(key, 0.0) + share
        return distribution

    def _apply_fuel_analytic_distribution(self):
        for expense in self.filtered("product_id.tms_spread_by_distance"):
            expense._default_analytic_distribution()
        return True
