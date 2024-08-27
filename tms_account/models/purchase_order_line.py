from odoo import api, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    @api.onchange("order_id", "trip_id")
    def _onchange_trip_id(self):
        if self.order_id and self.order_id.trip_id:
            self.analytic_distribution = self._default_analytic_distribution()

    def _default_analytic_distribution(self):
        if not self.order_id.trip_id:
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

        if self.order_id.trip_id.route_id and route_analytic_plan_group:
            analytic_account_id = self.order_id.trip_id.route_id.analytic_account_id.id
            analytic_accounts = self.env["account.analytic.account"].search(
                [("id", "=", analytic_account_id)]
            )
            account_id = str(analytic_accounts.id)
            # Set distribution as {account_ids: percentage}
            if account_id:
                analytic_account_ids.append(account_id)

        if order_analytic_plan_group:
            analytic_account_id = self.order_id.trip_id.analytic_account_id.id
            analytic_accounts = self.env["account.analytic.account"].search(
                [("id", "=", analytic_account_id)]
            )
            account_id = str(analytic_accounts.id)
            # Set distribution as {account_ids: percentage}
            if account_id:
                analytic_account_ids.append(account_id)

        distribution[", ".join(analytic_account_ids)] = 100

        return distribution
