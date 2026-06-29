# Copyright (C) 2024 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class TransportableProduct(models.Model):
    _name = "transportable.product"
    _description = "Transportable Product"

    vehicle_id = fields.Many2one("fleet.vehicle")
    product_id = fields.Many2one("product.product")
    capacity = fields.Float()
    measure_type = fields.Selection(
        [("unit", "Unit"), ("volume", "Volume")], string="Measure by:"
    )

    volume_uom = fields.Many2one(
        "uom.uom",
        domain=lambda self: self.env["res.config.settings"]._volume_domain(),
    )
    unit_uom = fields.Many2one(
        "uom.uom",
        domain=lambda self: self.env["res.config.settings"]._uom_hierarchy_domain(
            "uom.product_uom_unit"
        ),
    )
