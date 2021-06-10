# Copyright 2021 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import fields, models


class StockDock(models.Model):
    _name = "stock.dock"
    _description = "Dock, used by trucks to load/unload goods"

    name = fields.Char(required=True)
    barcode = fields.Char()
    active = fields.Boolean(string="Active", default=True)
