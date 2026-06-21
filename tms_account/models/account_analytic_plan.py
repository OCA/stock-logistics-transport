# Copyright (C) 2024 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class AccountAnalyticPlan(models.Model):
    _inherit = "account.analytic.plan"

    tms_flag = fields.Boolean(
        string="Used for Transports?",
        help="""This plan is used as a default in the Transport application.
        """,
        readonly=True,
    )
