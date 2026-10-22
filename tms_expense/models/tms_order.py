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
    currency_id = fields.Many2one(related="company_id.currency_id")
    trip_pay = fields.Monetary(string="Trip pay", currency_field="currency_id")
    expense_total = fields.Monetary(
        string="Expenses",
        currency_field="currency_id",
        compute="_compute_settlement",
    )
    settlement_balance = fields.Monetary(
        string="Owed to the driver",
        currency_field="currency_id",
        compute="_compute_settlement",
        help="Trip pay minus the expenses recorded on the trip.",
    )
    fuel_allocation_ids = fields.One2many("tms.expense.allocation", "trip_id")
    fuel_allocated = fields.Monetary(
        string="Fuel allocated",
        currency_field="currency_id",
        compute="_compute_fuel_allocated",
        help="Fuel cost assigned to this trip from fills spread by distance.",
    )

    @api.depends("driver_id")
    def _compute_driver_employee_id(self):
        for record in self:
            record.employee_id = self.env["hr.employee"].search(
                [("work_contact_id", "=", record.driver_id.partner_id.id)], limit=1
            )

    def write(self, vals):
        vehicles = self.mapped("vehicle_id")
        result = super().write(vals)
        if "stage_id" in vals:
            for order in self.filtered(lambda order: order.stage_id.is_completed):
                for expense in order.expense_ids.filtered(
                    lambda expense: expense.state == "draft"
                ):
                    expense.action_submit()
        if {
            "odometer_start",
            "odometer_end",
            "odometer_start_id",
            "odometer_end_id",
            "vehicle_id",
        } & set(vals):
            (vehicles | self.mapped("vehicle_id"))._reallocate_fuel_expenses()
        return result

    @api.depends("expense_ids", "expense_ids.total_amount")
    def _compute_expenses(self):
        for record in self:
            record.expense_count = len(record.expense_ids)

    @api.depends("expense_ids.total_amount", "trip_pay")
    def _compute_settlement(self):
        for order in self:
            total = sum(order.expense_ids.mapped("total_amount"))
            order.expense_total = total
            order.settlement_balance = order.trip_pay - total

    @api.depends("fuel_allocation_ids.amount")
    def _compute_fuel_allocated(self):
        for order in self:
            order.fuel_allocated = sum(order.fuel_allocation_ids.mapped("amount"))

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        orders.mapped("vehicle_id")._reallocate_fuel_expenses()
        return orders

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
