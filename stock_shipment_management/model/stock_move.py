# -*- coding: utf-8 -*-
#
#
#    Author: Yannick Vaucher
#    Copyright 2015 Camptocamp SA
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
#
import logging
from openerp import models, fields, api, _, exceptions

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'

    departure_shipment_id = fields.Many2one(
        'shipment.plan', 'Departure shipment',
        readonly=True,
    )
    arrival_shipment_id = fields.Many2one(
        'shipment.plan', 'Arrival shipment',
        readonly=True,
    )

    product_volume = fields.Float(
        related='product_id.volume',
        readonly=True,
        store=True
    )

    ship_partner_id = fields.Many2one(
        comodel_name='res.partner',
        compute='_get_ship_partner_id',
        string='Partner',
        readonly=True,
        store=True,
    )
    ship_carrier_id = fields.Many2one(
        related='departure_shipment_id.carrier_id',
        readonly=True,
        store=True
    )
    ship_carrier_tracking_ref = fields.Char(
        related='departure_shipment_id.carrier_tracking_ref',
        string='Tracking Ref.',
        readonly=True
    )
    ship_from_address_id = fields.Many2one(
        related='picking_id.origin_address_id',
        string='From Address',
        readonly=True,
        store=True
    )
    ship_to_address_id = fields.Many2one(
        related='picking_id.delivery_address_id',
        string='To Address',
        store=True
    )
    ship_consignee_id = fields.Many2one(
        related='picking_id.consignee_id',
        string='Consignee',
        readonly=True,
        store=True
    )
    ship_transport_mode_id = fields.Many2one(
        related='departure_shipment_id.transport_mode_id',
        string='Transport by',
        readonly=True,
    )
    ship_state = fields.Selection(
        related='departure_shipment_id.state',
        store=True,
    )
    ship_etd = fields.Datetime(
        related='date_expected',
        string='ETD',
        store=True
    )
    ship_eta = fields.Datetime(
        related='move_dest_id.date_expected',
        string='ETA',
        store=True
    )

    @api.one
    @api.depends('picking_id.sale_id',
                 'purchase_line_id.order_id')
    def _get_ship_partner_id(self):
        partner = False
        if self.picking_id.sale_id:
            partner = self.picking_id.sale_id.partner_id
        elif self.purchase_line_id.order_id.partner_id:
            partner = self.purchase_line_id.order_id.partner_id
        self.ship_partner_id = partner

    @api.multi
    def action_cancel(self):
        """ Forbid to cancel a shipment arrival move if it's departure move
        is not canceled.

        As dest_move are canceled before origin moves, we check that

        """
        cancel_list = self.env.context.get('cancel_list', [])
        for move in self:
            if (
                move.arrival_shipment_id and
                not (move.move_orig_ids.state == 'cancel' or
                     set(move.move_orig_ids.ids).issubset(set(cancel_list))
                     )
            ):
                raise exceptions.Warning(
                    _('You cannot cancel a shipment arrival stock move that '
                      'depends on an uncancelled shipment departure stock '
                      'move.'))
            cancel_list.append(move.id)
        return super(StockMove, self.with_context(cancel_list=cancel_list)
                     ).action_cancel()

    @api.multi
    def write(self, values):
        res = super(StockMove, self).write(values)
        if values.get('state', '') in ('done', 'cancel'):
            for ship in self.mapped('arrival_shipment_id'):
                if ship.state == 'in_transit':
                    ship.signal_workflow('transit_end')
        return res

    @api.multi
    def _picking_assign(self, procurement_group, location_from, location_to):
        """ When an arrival transit move is split, we create a backorder

        """
        res = super(StockMove, self)._picking_assign(
            procurement_group, location_from, location_to)
        if self.env.context.get('split_transit_arrival') == 'arrival':
            context = {'do_only_split': True}
            Picking = self.env['stock.picking'].with_context(**context)
            Picking._create_backorder(self.picking_id, backorder_moves=self)
        return res

    @api.model
    def split(self, move, qty,
              restrict_lot_id=False, restrict_partner_id=False):
        """ Propagate the splitting of a departure transit move to
        its arrival transit move

        Here, we remove picking_id to force arrival move to trigger
        _picking_assign for new move

        """
        context = {}
        if move.departure_shipment_id:
            context['split_transit_arrival'] = 'departure'
        # On propagate split
        if self.env.context.get('split_transit_arrival') == 'departure':
            context['split_transit_arrival'] = 'arrival'

        _self = self.with_context(**context)
        res = super(StockMove, _self).split(
            move, qty,
            restrict_lot_id=restrict_lot_id,
            restrict_partner_id=restrict_partner_id)
        return res

    @api.multi
    def copy(self, default=None):
        """ Ensure an arrival move from Transit is not assigned to same picking
        when source move is split

        """
        if default is None:
            default = {}
        if self.env.context.get('split_transit_arrival') == 'arrival':
            default['picking_id'] = False
        return super(StockMove, self).copy(default=default)

    @api.multi
    def action_remove_from_shipment(self):
        self.move_dest_id.arrival_shipment_id = False
        self.departure_shipment_id = False
        return True
