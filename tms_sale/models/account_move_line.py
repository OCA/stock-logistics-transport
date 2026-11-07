# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    tms_rate_price = fields.Monetary(
        string="Rate price",
        currency_field="tms_rate_currency_id",
        copy=False,
        help="Unit price in the rate card currency, before conversion.",
    )
    tms_rate_currency_id = fields.Many2one(
        "res.currency",
        string="Rate currency",
        copy=False,
    )
    tms_rate_exchange = fields.Float(
        string="Exchange rate",
        digits=(16, 6),
        copy=False,
    )
    tms_rate_date = fields.Date(string="Exchange date", copy=False)
