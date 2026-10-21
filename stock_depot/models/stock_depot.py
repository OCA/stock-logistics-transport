# Copyright 2024 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class StockDepot(models.Model):
    _name = "stock.depot"
    _description = "Partner depot"

    name = fields.Char(required=True)
    partner_id = fields.Many2one("res.partner", required=True)
