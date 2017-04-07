# -*- coding: utf-8 -*-
# © 2016 initOS GmbH
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, api


class StockPicking(models.Model):

    _inherit = 'stock.picking'

    @api.multi
    def _get_dict(self):
        result = {}
        for record in self.search([('carrier_tracking_ref', '!=', False)]):
                result = self.env['stock.picking.delivery'].create({
                    'carrier_id': record.carrier_id.id,
                    'carrier_tracking_ref': record.carrier_tracking_ref,
                    'picking_id': record.id})
        return result

    @api.model
    def _carrier_migration(self):
        pickings = self.search([('carrier_tracking_ref', '!=', False)])
        for picking in pickings:
            if picking.carrier_tracking_ref:
                self._get_dict()
        return