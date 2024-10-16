# Copyright (C) 2024 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class AnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    trip_id = fields.One2many("tms.order", "analytic_account_id", copy=False)
    route_id = fields.One2many("tms.route", "analytic_account_id", copy=False)
