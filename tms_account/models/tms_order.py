# Copyright (C) 2024 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models


class TMSOrder(models.Model):
    _inherit = "tms.order"

    invoice_count = fields.Integer(
        compute="_compute_get_invoiced",
        readonly=True,
        copy=False,
    )
    bill_count = fields.Integer(
        compute="_compute_get_invoiced",
        readonly=True,
        copy=False,
    )

    create_invoice = fields.Boolean(string="Create invoices and bills when completed?")

    analytic_account_id = fields.Many2one("account.analytic.account", copy=False)

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

    @api.model
    def create(self, vals):
        order = super().create(vals)
        if self.env.user.has_group(
            "analytic.group_analytic_accounting"
        ) and self.env.user.has_group("tms_account.group_tms_order_analytic_plan"):
            analytic_account = self.env["account.analytic.account"].create(
                {
                    "name": vals.get("name"),
                    "plan_id": self.env.ref("tms_account.tms_order_analytic_plan").id,
                    "trip_id": order,
                }
            )
            order.analytic_account_id = analytic_account
        return order

    @api.model
    def write(self, vals):
        order = super().write(vals)
        if "stage_id" in vals:
            stage = self.env["tms.stage"].search([("id", "=", vals["stage_id"])])
            if stage.is_completed and self.create_invoice:
                if self.sale_id:
                    self._handle_invoices()
                if self.purchase_ids:
                    self._handle_bills()
        return order

    def _handle_invoices(self):
        all_completed = True
        for line in self.sale_id.order_line:
            if line.tms_order_ids.id == self.id:
                line.qty_delivered = line.product_uom_qty
            if not line.tms_order_ids.stage_id.is_completed:
                all_completed = False

        if not self.sale_id.invoice_ids and all_completed:
            invoice = self.sale_id._create_invoices()

            # Check if analytic accounting is enabled
            if self.env.user.has_group("analytic.group_analytic_accounting"):
                self._assign_analytic_accounts(invoice)

    def _assign_analytic_accounts(self, invoice):
        # Fetch the analytic distribution
        distribution = self._default_analytic_distribution()

        # If distribution is not empty, assign it to the invoice lines
        if distribution:
            for line in invoice.invoice_line_ids:
                line.analytic_distribution = distribution

    def _default_analytic_distribution(self):
        # Ensure there are tms_order_ids to work with
        if not self.sale_id.tms_order_ids:
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

        # Iterate over tms_order_ids to determine analytic accounts
        for tms_order in self.sale_id.tms_order_ids:
            if tms_order.route_id and route_analytic_plan_group:
                analytic_account_id = tms_order.route_id.analytic_account_id.id
                analytic_accounts = self.env["account.analytic.account"].search(
                    [("id", "=", analytic_account_id)]
                )
                account_id = str(analytic_accounts.id)
                if account_id:
                    analytic_account_ids.append(account_id)

            if order_analytic_plan_group:
                analytic_account_id = tms_order.analytic_account_id.id
                analytic_accounts = self.env["account.analytic.account"].search(
                    [("id", "=", analytic_account_id)]
                )
                account_id = str(analytic_accounts.id)
                if account_id:
                    analytic_account_ids.append(account_id)

        # Ensure distribution is provided with unique analytic accounts
        analytic_account_ids = list(set(analytic_account_ids))
        if analytic_account_ids:
            distribution[", ".join(analytic_account_ids)] = 100

        return distribution

    def _handle_bills(self):
        for purchase in self.purchase_ids:
            purchase.action_create_invoice()
        return

    @api.depends("stage_id")
    def _compute_get_invoiced(self):
        for trip in self:
            trip.bill_count = 0
            trip.invoice_count = trip.sale_id.invoice_count

            # Filter purchases that have at least one bill
            purchase_with_bills = self.env["purchase.order"].search(
                [("id", "in", trip.purchase_ids.ids), ("invoice_ids", "!=", False)]
            )

            # Count the number of such purchases
            trip.bill_count = len(purchase_with_bills)

    def action_view_invoices(self):
        action = self.sale_id.action_view_invoice()
        return action

    def action_view_bills(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "tree,form",
            "domain": [
                ("line_ids.purchase_line_id.order_id.trip_id", "=", self.id),
                ("move_type", "=", "in_invoice"),
            ],
            "name": _("Bills for Trip %s") % self.name,
        }

    def action_view_analytic_account(self):
        self.ensure_one()
        analytic_account = self.env["account.analytic.account"].search(
            [("trip_id", "=", self.id)], limit=1
        )

        if analytic_account:
            return {
                "type": "ir.actions.act_window",
                "res_model": "account.analytic.account",
                "view_mode": "form",
                "res_id": analytic_account.id,
                "name": _("Analytic Account for Trip %s") % self.name,
            }
