# -*- coding: utf-8 -*-
# © 2016 initOS GmbH
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, api


class StockPicking(models.Model):

    _inherit = 'stock.picking'

    @api.model
    def _carrier_migration(self):
        pickings = self.search([('carrier_tracking_ref', '!=', False)])
        for picking in pickings:
            if picking.carrier_tracking_ref:
                self.env['stock.picking.delivery'].\
                    create({'carrier_id': picking.carrier_id.id,
                            'carrier_tracking_ref':
                            picking.carrier_tracking_ref,
                            'picking_id': picking.id})
        return super(StockPicking, self)._carrier_migration()
