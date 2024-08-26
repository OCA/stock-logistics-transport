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

    analytic_account_id = fields.Many2one("account.analytic.account")

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
        super().write(vals)
        if "stage_id" in vals:
            stage = self.env["tms.stage"].search(
                [
                    ("id", "=", vals["stage_id"]),
                ]
            )
            if stage.is_completed and self.create_invoice:
                if self.sale_id:
                    all_completed = True
                    for line in self.sale_id.order_line:
                        if line.tms_order_id.id == self.id:
                            line.qty_delivered = line.product_uom_qty
                        if not line.tms_order_id.stage_id.is_completed:
                            all_completed = False
                    if not self.sale_id.invoice_ids and all_completed:
                        self.sale_id._create_invoices()
                if self.purchase_ids:
                    for purchase in self.purchase_ids:
                        purchase.action_create_invoice()
        return

    @api.depends("stage_id")
    def _compute_get_invoiced(self):
        for trip in self:
            trip.bill_count = 0
            trip.invoice_count = trip.sale_id.invoice_count

            for purchase in trip.purchase_ids:
                for line in purchase.order_line:
                    trip.bill_count += line.qty_invoiced

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
