# Copyright 2024 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    shipment_advice_id = fields.Many2one(
        comodel_name="shipment.advice", ondelete="set null", index=True
    )
