# Copyright (C) 2024 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class TMSOrder(models.Model):
    _inherit = "tms.order"

    expense_ids = fields.One2many(
        "hr.expense",
        "trip_id",
    )

    employee_id = fields.Many2one(
        "hr.employee",
        string="Driver",
        compute="_compute_driver_employee_id",
        store=True,
    )

    expense_count = fields.Integer(compute="_compute_expenses")

    @api.depends("driver_id")
    def _compute_driver_employee_id(self):
        for record in self:
            record.employee_id = self.env["hr.employee"].search(
                [("work_contact_id", "=", record.driver_id.id)], limit=1
            )
            if not record.employee_id:
                record.employee_id = self.env["hr.employee"].search(
                    [("address_id", "=", record.driver_id.id)], limit=1
                )

    @api.model
    def write(self, vals):
        result = super().write(vals)
        if "stage_id" in vals:
            if vals["stage_id"] == 3:
                for expense in self.expense_ids:
                    if expense.state != "reported":
                        expense.action_submit_expenses()
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
            "view_mode": "tree,form",
            "domain": [("trip_id", "=", self.id)],
            "context": {"default_trip_id": self.id},
            "name": _("Expenses for Trip %s") % self.name,
        }
