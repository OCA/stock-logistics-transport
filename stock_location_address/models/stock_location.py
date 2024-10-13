#  Copyright 2018 Creu Blanca
#  License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class StockLocation(models.Model):
    _inherit = "stock.location"

    address_id = fields.Many2one(comodel_name="res.partner", string="Address")
    real_address_id = fields.Many2one(
        comodel_name="res.partner",
        string="Real Address",
        compute="_compute_real_address_id",
    )

    def _get_parent_address(self):
        if self.location_id and self.location_id.address_id:
            return self.location_id.address_id
        elif self.location_id:
            return self.location_id._get_parent_address()
        else:
            return self.env["res.partner"]

    @api.depends("address_id", "location_id")
    def _compute_real_address_id(self):
        for record in self:
            if record.address_id:
                record.real_address_id = record.address_id
            elif record.location_id:
                record.real_address_id = record._get_parent_address()
            else:
                record.real_address_id = False
