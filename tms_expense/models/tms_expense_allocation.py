# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class TmsExpenseAllocation(models.Model):
    _name = "tms.expense.allocation"
    _description = "Trip share of an expense spread by distance"
    _order = "distance desc, id"

    expense_id = fields.Many2one(
        "hr.expense",
        required=True,
        ondelete="cascade",
        index=True,
    )
    trip_id = fields.Many2one(
        "tms.order",
        string="Trip",
        required=True,
        ondelete="cascade",
        index=True,
    )
    currency_id = fields.Many2one(related="expense_id.currency_id")
    distance = fields.Float()
    amount = fields.Monetary(currency_field="currency_id")
