# Copyright 2024 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import fields, models


class WizardStockMoveSplit(models.TransientModel):
    _name = "wizard.stock.move.split"
    _description = "Stock Move Split Wizard"

    move_id = fields.Many2one(comodel_name="stock.move")
    quantity_to_split = fields.Float()
