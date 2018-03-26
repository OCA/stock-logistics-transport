#  Copyright 2018 Creu Blanca
#  License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, models, fields


class StockLocation(models.Model):
    _inherit = 'stock.location'

    address_id = fields.Many2one(
        comodel_name='res.partner',
        string='Address',
    )
    real_address_id = fields.Many2one(
        comodel_name='res.partner',
        string='Address',
        compute='_compute_real_address_id',
    )

    @api.depends('address_id', 'location_id')
    def _compute_real_address_id(self):
        for record in self:
            if record.address_id:
                record.real_address_id = record.address_id
            elif record.location_id:
                record.real_address_id = record.location_id.real_address_id
