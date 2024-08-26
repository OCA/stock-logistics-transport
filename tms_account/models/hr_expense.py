from odoo import api, fields, models


class HrExpense(models.Model):
    _inherit = "hr.expense"

    analytic_distribution = fields.Json()

    @api.onchange("id", "trip_id")
    def _onchange_trip_id(self):
        # Update analytic_distribution when trip_id changes
        if self.trip_id:
            self.analytic_distribution = self._default_analytic_distribution()

    @api.model
    def default_get(self, fields):
        # Ensure default values are set when creating a new record
        res = super().default_get(fields)
        if "analytic_distribution" in fields:
            res["analytic_distribution"] = self._default_analytic_distribution()
        return res

    def _default_analytic_distribution(self):
        trip = self.env.context.get("default_trip_id")
        if not trip:
            return {}

        # Initialize distribution dictionary
        distribution = {}

        # Fetch the analytic accounts based on group names
        route_analytic_plan_group = self.env.ref(
            "tms_account.group_tms_route_analytic_plan"
        )
        order_analytic_plan_group = self.env.ref(
            "tms_account.group_tms_order_analytic_plan"
        )

        analytic_account_ids = []

        trip_id = self.env["tms.order"].browse(trip)

        # Check and add analytic accounts for route_id
        if trip_id.route_id and route_analytic_plan_group:
            analytic_account_id = trip_id.route_id.analytic_account_id.id
            if analytic_account_id:
                # Convert to string and add to list
                analytic_account_ids.append(str(analytic_account_id))

        # Check and add analytic accounts for trip_id
        if order_analytic_plan_group:
            analytic_account_id = trip_id.analytic_account_id.id
            if analytic_account_id:
                # Convert to string and add to list
                analytic_account_ids.append(str(analytic_account_id))

        # Set distribution with concatenated account IDs as key and percentage as value
        if analytic_account_ids:
            distribution[",".join(analytic_account_ids)] = 100.0

        self.analytic_distribution = distribution

        return distribution
