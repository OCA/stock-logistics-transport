# Copyright 2018 Creu Blanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.onchange("picking_type_id")
    def _onchange_picking_type_id(self):
        location = self.picking_type_id.default_location_dest_id
        if location.usage == "internal":
            self.dest_address_id = location.real_address_id
            return
        super()._onchange_picking_type_id()

    def _get_destination_location(self):
        self.ensure_one()
        lc = self.picking_type_id.default_location_dest_id
        if self.dest_address_id and lc.real_address_id == self.dest_address_id:
            return lc.id
        return super()._get_destination_location()
