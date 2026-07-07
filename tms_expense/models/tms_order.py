# Copyright (C) 2024 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class TMSOrder(models.Model):
    _inherit = "tms.order"

    expense_ids = fields.One2many(
        "hr.expense",
        "trip_id",
    )

    employee_id = fields.Many2one(
        "hr.employee",
        string="Driver Employee",
        compute="_compute_driver_employee_id",
        store=True,
    )

    expense_count = fields.Integer(compute="_compute_expenses")

    @api.depends("driver_id")
    def _compute_driver_employee_id(self):
        for record in self:
            record.employee_id = self.env["hr.employee"].search(
                [("work_contact_id", "=", record.driver_id.partner_id.id)], limit=1
            )

    def write(self, vals):
        result = super().write(vals)
        if "stage_id" in vals:
            for order in self.filtered(lambda o: o.stage_id.is_completed):
                for expense in order.expense_ids.filtered(lambda e: e.state == "draft"):
                    expense.action_submit()
        return result

    @api.depends("expense_ids")
    def _compute_expenses(self):
        for record in self:
            record.expense_count = len(record.expense_ids)

    def action_view_expenses(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "hr.expense",
            "view_mode": "list,form",
            "domain": [("trip_id", "=", self.id)],
            "context": {"default_trip_id": self.id},
            "name": self.env._("Expenses for Trip %s", self.name),
        }
