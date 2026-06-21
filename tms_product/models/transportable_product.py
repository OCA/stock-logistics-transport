# Copyright (C) 2024 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class TransportableProduct(models.Model):
    _name = "transportable.product"

    vehicle_id = fields.Many2one("fleet.vehicle")
    product_id = fields.Many2one("product.product")
    capacity = fields.Float()
    measure_type = fields.Selection(
        [("unit", "Unit"), ("volume", "Volume")], string="Measure by:"
    )

    volume_uom = fields.Many2one(
        "uom.uom",
        domain=lambda self: [
            ("category_id", "=", self.env.ref("uom.product_uom_categ_vol").id)
        ],
    )
    unit_uom = fields.Many2one(
        "uom.uom",
        domain=lambda self: [
            ("category_id", "=", self.env.ref("uom.product_uom_categ_unit").id)
        ],
    )
