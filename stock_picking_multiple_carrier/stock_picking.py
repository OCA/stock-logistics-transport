# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 initOS GmbH (<http://www.initos.com>).
#    Author Rami Alwafaie <rami.alwafaie at initos.com>
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

from openerp import models, fields, api


class StockPickingDelivery(models.Model):

    _name = 'stock.picking.delivery'

    carrier_id = fields.Many2one("delivery.carrier",
                                 string="Carrier",
                                 )
    carrier_tracking_ref = fields.Char("Carrier Tracking Ref",
                                       size=32,
                                       required=True,)
    picking_id = fields.Many2one("stock.picking",
                                 string="Picking",
                                 required=True)


@api.model
def _carrier_tracking_ref_display(self):
    # use this function with the functional field "carrier_tracking_ref"
    # in StockPicking class
    # to show the carrier information in another module
    # (in sale order for example)
        pickings = self.browse()
        deliveries = dict([(picking.id, picking.delivery_ids)
                           for picking in pickings])
        result = {}
        for record_id in pickings:
            refs = map(lambda delivery:
                       (delivery.carrier_id.name or '') + ': ' +
                       (delivery.carrier_tracking_ref or ''),
                       deliveries[record_id])
            result[record_id] = ', '.join(refs)
        return result


class StockPicking(models.Model):

    _inherit = 'stock.picking'

    delivery_ids = fields.One2many("stock.picking.delivery",
                                   "picking_id",
                                   string="Delivery Information")
    carrier_tracking_ref = fields.Char(compute=_carrier_tracking_ref_display,
                                       string="Carrier Tracking Refs")
