# Copyright (C) 2024 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class TMSRoute(models.Model):
    _inherit = "tms.route"

    analytic_plan_id = fields.Many2one("account.analytic.plan")
    analytic_account_id = fields.Many2one("account.analytic.account")
