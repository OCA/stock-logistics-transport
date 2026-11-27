# Copyright (C) 2024 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle"

    product_id = fields.Many2one("product.product", readonly=True)
    lot_id = fields.Many2one("stock.lot", string="Serial #", readonly=True)
    stock_picking_id = fields.Many2one("stock.picking")

    transportable_product_ids = fields.One2many("transportable.product", "vehicle_id")
    cargo_type = fields.Selection(
        [("volume", "Volume"), ("products", "Products")],
        compute="_compute_cargo_type",
        store=True,
        readonly=False,
    )

    @api.depends("operation")
    def _compute_cargo_type(self):
        for record in self:
            if record.operation == "passenger":
                record.cargo_type = False
