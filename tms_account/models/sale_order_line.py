# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _default_analytic_distribution(self):
        total_distribution = {}
        for trip in self.tms_order_ids:
            trip_count = len(self.tms_order_ids)
            percentage_per_trip = 100 / trip_count

            route_analytic_plan_group = self.env.ref(
                "tms_account.group_tms_route_analytic_plan"
            )
            order_analytic_plan_group = self.env.ref(
                "tms_account.group_tms_order_analytic_plan"
            )
            analytic_account_ids = []

            trip_id = self.env["tms.order"].browse(trip.id)

            if trip_id.route_id and route_analytic_plan_group:
                analytic_account_id = trip_id.route_id.analytic_account_id.id
                if analytic_account_id:
                    analytic_account_ids.append(str(analytic_account_id))

            if order_analytic_plan_group:
                analytic_account_id = trip_id.analytic_account_id.id
                if analytic_account_id:
                    analytic_account_ids.append(str(analytic_account_id))

            if analytic_account_ids:
                distribution_key = ",".join(analytic_account_ids)
                total_distribution[distribution_key] = percentage_per_trip

        self.analytic_distribution = total_distribution

        return total_distribution

    def _prepare_invoice_line(self, **optional_values):
        res = super()._prepare_invoice_line(**optional_values)
        if not self.display_type:
            res.update(
                {
                    "tms_factor": self.tms_factor,
                    "tms_factor_uom": self.tms_factor_uom,
                }
            )
            self._set_analytic_distribution(res, **optional_values)
        return res
