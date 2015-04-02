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
#    GNU Affero General Public License for more description.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#
from openerp import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    to_transit_moves_count = fields.Integer(
        compute='_count_to_transit_moves'
    )

    @api.multi
    def _get_to_transit_moves(self):
        """ Get moves related to Sale order going to transit location"""
        moves = self.picking_ids.mapped('move_lines')
        return moves.filtered(
            lambda rec: rec.location_dest_id.usage == 'transit')

    @api.one
    @api.depends('picking_ids.move_lines.location_dest_id.usage')
    def _count_to_transit_moves(self):
        """ Count moves related to Sale order going to transit location"""
        self.to_transit_moves_count = len(self._get_to_transit_moves())

    @api.multi
    def action_open_to_transit_moves(self):
        """ Open move list view of to transit moves """
        action_ref = ('stock_shipment_management'
                      '.action_move_transit_pipeline_waiting')
        action_dict = self.env.ref(action_ref).read()[0]
        moves = self._get_to_transit_moves()
        action_dict['domain'] = [('id', 'in', moves.ids)]
        return action_dict
