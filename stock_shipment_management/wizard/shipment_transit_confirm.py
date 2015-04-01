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
from openerp import fields, models, api, _


class ShipmentTransitConfirm(models.TransientModel):
    _name = 'shipment.transit.confirm'

    @api.depends('shipment_id.departure_move_ids.state')
    def _get_undone_move_ids(self):
        """ get undone departure moves of shipment
        """
        moves = self.shipment_id.departure_move_ids
        moves = moves.filtered(lambda m: m.state not in ('done', 'cancel'))
        self.undone_move_ids = moves

    shipment_id = fields.Many2one(
        'shipment.plan', 'Shipment',
        default=lambda self: self.env.context.get('active_id', False) or False
    )
    undone_move_ids = fields.One2many(
        compute='_get_undone_move_ids',
        comodel_name='stock.move',
        string='Selected Moves',
    )

    @api.multi
    def action_confirm(self):
        """ Remove undone move from shipment when confirmed by the user"""
        arrival_moves = self.undone_move_ids.mapped('move_dest_id')
        self.undone_move_ids.write({'departure_shipment_id': False})
        arrival_moves.write({'arrival_shipment_id': False})
        self.shipment_id.signal_workflow('transit_start')
        return True

    @api.multi
    def action_open_window(self):
        view = self.env.ref(
            'stock_shipment_management.view_shipment_transit_confirm')
        action = {
            'name': _("Remove undone departure moves?"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'shipment.transit.confirm',
            'view_id': [view.id],
            'target': 'new',
            'nodestroy': True,
            'res_id': self.id,
        }
        return action
