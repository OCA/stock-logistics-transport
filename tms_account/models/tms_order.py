# Copyright (C) 2024 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


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

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        if not (
            self.env.user.has_group("analytic.group_analytic_accounting")
            and self.env.user.has_group("tms_account.group_tms_order_analytic_plan")
        ):
            return orders
        plan = self.env.ref("tms_account.tms_order_analytic_plan")
        for order, vals in zip(orders, vals_list, strict=True):
            analytic_account = self.env["account.analytic.account"].create(
                {
                    "name": vals.get("name") or order.name,
                    "plan_id": plan.id,
                }
            )
            order.analytic_account_id = analytic_account
        return orders

    def write(self, vals):
        res = super().write(vals)
        if "stage_id" in vals:
            stage = self.env["tms.stage"].browse(vals["stage_id"])
            for order in self:
                if stage.is_completed and order.create_invoice:
                    if order.sale_id:
                        order._handle_invoices()
                    if order.purchase_ids:
                        order._handle_bills()
        return res

    def _handle_invoices(self):
        self.ensure_one()
        all_completed = True
        for line in self.sale_id.order_line:
            if line.tms_order_ids.id == self.id:
                line.qty_delivered = line.product_uom_qty
            if not line.tms_order_ids.stage_id.is_completed:
                all_completed = False

        if not self.sale_id.invoice_ids and all_completed:
            invoice = self.sale_id._create_invoices()

            if self.env.user.has_group("analytic.group_analytic_accounting"):
                self._assign_analytic_accounts(invoice)

    def _assign_analytic_accounts(self, invoice):
        distribution = self._default_analytic_distribution()
        if distribution:
            for line in invoice.invoice_line_ids:
                line.analytic_distribution = distribution

    def _default_analytic_distribution(self):
        if not self.sale_id.tms_order_ids:
            return {}

        distribution = {}
        route_analytic_plan_group = self.env.ref(
            "tms_account.group_tms_route_analytic_plan"
        )
        order_analytic_plan_group = self.env.ref(
            "tms_account.group_tms_order_analytic_plan"
        )
        analytic_account_ids = []

        for tms_order in self.sale_id.tms_order_ids:
            if tms_order.route_id and route_analytic_plan_group:
                analytic_account_id = tms_order.route_id.analytic_account_id.id
                if analytic_account_id:
                    analytic_account_ids.append(str(analytic_account_id))

            if order_analytic_plan_group:
                analytic_account_id = tms_order.analytic_account_id.id
                if analytic_account_id:
                    analytic_account_ids.append(str(analytic_account_id))

        analytic_account_ids = list(set(analytic_account_ids))
        if analytic_account_ids:
            distribution[", ".join(analytic_account_ids)] = 100

        return distribution

    def _handle_bills(self):
        self.ensure_one()
        for purchase in self.purchase_ids:
            purchase.action_create_invoice()

    @api.depends("stage_id")
    def _compute_get_invoiced(self):
        for trip in self:
            trip.bill_count = 0
            trip.invoice_count = trip.sale_id.invoice_count

            purchase_with_bills = self.env["purchase.order"].search(
                [("id", "in", trip.purchase_ids.ids), ("invoice_ids", "!=", False)]
            )
            trip.bill_count = len(purchase_with_bills)

    def action_view_invoices(self):
        self.ensure_one()
        return self.sale_id.action_view_invoice()

    def action_view_bills(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [
                ("line_ids.purchase_line_id.order_id.trip_id", "=", self.id),
                ("move_type", "=", "in_invoice"),
            ],
            "name": self.env._("Bills for Trip %s", self.name),
        }

    def action_view_analytic_account(self):
        self.ensure_one()
        if self.analytic_account_id:
            return {
                "type": "ir.actions.act_window",
                "res_model": "account.analytic.account",
                "view_mode": "form",
                "res_id": self.analytic_account_id.id,
                "name": self.env._("Analytic Account for Trip %s", self.name),
            }
        return False
