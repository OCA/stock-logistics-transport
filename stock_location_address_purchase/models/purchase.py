# Copyright 2018 Creu Blanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.depends("picking_type_id")
    def _compute_dest_address_id(self):
        res = super()._compute_dest_address_id()
        for po in self:
            if po.picking_type_id.default_location_dest_id.usage == "internal":
                po.dest_address_id = (
                    po.picking_type_id.default_location_dest_id.real_address_id
                )
        return res

    def _get_destination_location(self):
        self.ensure_one()
        lc = self.picking_type_id.default_location_dest_id
        if self.dest_address_id and lc.real_address_id == self.dest_address_id:
            return lc.id
        return super()._get_destination_location()
