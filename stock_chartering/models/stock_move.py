from odoo import fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    container = fields.Char(related="picking_id.container")
