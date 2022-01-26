# Copyright 2022 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    shipment_planning_id = fields.Many2one(
        comodel_name="shipment.planning",
        index=True,
    )
