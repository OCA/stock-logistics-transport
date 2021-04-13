# Copyright 2021 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class StockRule(models.Model):

    _inherit = 'stock.rule'

    def _prepare_purchase_order(
        self, product_id, product_qty, product_uom, origin, values, partner
    ):
        res = super()._prepare_purchase_order(
            product_id, product_qty, product_uom, origin, values, partner)
        location = self.picking_type_id.default_location_dest_id
        if not res.get("dest_address_id", False) and location.usage == 'internal':
            res["dest_address_id"] = location.real_address_id.id
        return res
