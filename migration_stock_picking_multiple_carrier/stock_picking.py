# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Rami Alwafaie
#    Copyright 2015 initOS GmbH
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, api


class stock_picking(models.Model):

    _inherit = 'stock.picking'

    @api.model
    def _carrier_migration(self):
        pickings = self.search([])
        for picking in pickings:
            if picking.carrier_tracking_ref:
                delivery_ids = self.env['stock.picking.delivery'].\
                    create({'carrier_id': picking.carrier_id.id,
                            'carrier_tracking_ref': picking.carrier_tracking_ref,
                            'picking_id': picking.id})
        return
