# -*- coding: utf-8 -*-
# © 2015 Camptocamp SA - Alexandre Fayolle
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
from openerp import models, fields, api


_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.multi
    def _picking_assign(self, procurement_group, location_from, location_to):
        # note: we cannot rely on the procurement_group argument which can be
        # empty, in which case the super() implementation will create a new
        # group -> we use the procurement.group of the picking.
        _super = super(StockMove, self)
        res = _super._picking_assign(procurement_group,
                                     location_from,
                                     location_to)
        for picking in self.mapped('picking_id'):
            group = picking.group_id
            if not group:
                continue
            changes = {}
            if not picking.consignee_id:
                changes['consignee_id'] = group.consignee_id.id
            if not picking.delivery_address_id:
                changes['delivery_address_id'] = group.delivery_address_id.id
            if not picking.origin_address_id:
                # for the origin address, the information on the
                # procurement.order trumps the information on the procurement
                # group.
                origin_address = picking.mapped(
                    'move_lines.procurement_id.origin_address_id'
                    )
                if len(origin_address) > 1:
                    _logger.error(
                        'more than one origin address found for picking %s',
                        picking
                        )
                    origin_address = origin_address[0]
                if not origin_address:
                    # nothing on the procurements, use the information from the
                    # group
                    origin_address = group.origin_address_id
                changes['origin_address_id'] = origin_address.id
            picking.write(changes)
        return res

    @api.model
    def _prepare_procurement_from_move(self, move):
        _super = super(StockMove, self)
        res = _super._prepare_procurement_from_move(move)
        update = {
            'origin_address_id': move.procurement_id.origin_address_id.id
            }
        res.update(update)
        return res


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    consignee_id = fields.Many2one(
        comodel_name='res.partner',
        string='Consignee',
        domain=[('is_consignee', '=', True)],
        help='The person to whom the shipment is to be delivered'
    )

    delivery_address_id = fields.Many2one(
        comodel_name='res.partner',
        string='Delivery Address',
        help='The delivery address of the shipment'
    )

    origin_address_id = fields.Many2one(
        comodel_name='res.partner',
        string='Origin Address',
        help='The origin address of the shipment'
    )
