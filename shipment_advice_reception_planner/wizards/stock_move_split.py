# Copyright 2024 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import fields, models


class WizardStockMoveSplit(models.TransientModel):
    _name = "wizard.stock.move.split"
    _description = "Stock Move Split Wizard"

    move_id = fields.Many2one(comodel_name="stock.move")
    quantity_to_split = fields.Float()

    def _split_move(self):
        qty = self.move_id.product_uom._compute_quantity(
            self.quantity_to_split, self.move_id.product_id.uom_id
        )
        move_vals = self.move_id._split(qty)
        return self.env["stock.move"].create(move_vals)
