from odoo import fields, models


class FreightContainer(models.Model):
    _name = "freight.container"
    _description = "Goods container"
    _order = "name"

    name = fields.Char(required=True)
