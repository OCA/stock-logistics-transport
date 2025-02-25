# Copyright 2021 Creu Blanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class StockRule(models.Model):

    _inherit = "stock.rule"

    def _prepare_purchase_order(self, company_id, origins, values):
        res = super()._prepare_purchase_order(company_id, origins, values)
        location = self.picking_type_id.default_location_dest_id
        if not res.get("dest_address_id", False) and location.usage == "internal":
            res["dest_address_id"] = location.real_address_id.id
        return res
