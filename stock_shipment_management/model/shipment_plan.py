# -*- coding: utf-8 -*-
#
#
#    Authors: Joël Grand-Guillaume, Yannick Vaucher
#    Copyright 2013-2015 Camptocamp SA
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
import time
import logging
from openerp import fields, models, api, exceptions, _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as DT_FORMAT
from openerp.addons.purchase import purchase

_logger = logging.getLogger(__name__)


class ShipmentPlan(models.Model):
    _name = "shipment.plan"
    _inherit = ['mail.thread']

    _description = "Shipment Plan"

    name = fields.Char(
        'Reference',
        required=True,
        readonly=True,
        default='/',
        copy=False,
    )
    user_id = fields.Many2one(
        'res.users', 'Responsible',
        readonly=True,
        states={'draft': [('readonly', False)]},
        default=lambda self: self.env.uid,
    )
    purchase_id = fields.Many2one(
        'purchase.order',
        'Purchase Order',
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    po_state = fields.Selection(
        related='purchase_id.state',
        selection=purchase.purchase_order.STATE_SELECTION,
        string='PO State',
    )
    carrier_id = fields.Many2one(
        'delivery.carrier',
        'Carrier',
        readonly=True,  # updated by wizard
        track_visibility='onchange',
    )
    initial_etd = fields.Datetime(
        'Initial ETD',
        readonly=True,
        states={'draft': [('readonly', False)]},
        help="Initial Estimated Time of Departure"
    )
    initial_eta = fields.Datetime(
        'Initial ETA',
        readonly=True,
        states={'draft': [('readonly', False)]},
        help="Initial Estimated Time of Arrival"
    )
    etd = fields.Datetime(
        'ETD',
        readonly=True,  # updated by wizard
        track_visibility='onchange',
        help="Up to date Estimated Time of Departure"
    )
    eta = fields.Datetime(
        'ETA',
        readonly=True,  # updated by wizard
        track_visibility='onchange',
        help="Up to date Estimated Time of Arrival"
    )
    from_address_id = fields.Many2one(
        'res.partner', 'From Address',
        readonly=True,  # You can't update the from address
        required=True,
    )
    to_address_id = fields.Many2one(
        'res.partner',
        'To Address',
        readonly=True,  # updated by wizard
        track_visibility='onchange',
        required=True,
    )
    consignee_id = fields.Many2one(
        'res.partner',
        'Consignee',
        readonly=True,  # updated by wizard
        track_visibility='onchange',
        domain=[('is_consignee', '=', True)],
    )
    carrier_tracking_ref = fields.Char(
        'Tracking Ref.',
        readonly=True,  # updated by wizard
        track_visibility='onchange',
    )
    transport_mode_id = fields.Many2one(
        'transport.mode',
        string='Transport by',
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    note = fields.Text(
        'Description / Remarks',
        readonly=True,
        states={'draft': [('readonly', False)]}
    )
    state = fields.Selection(
        [('draft', 'Draft'),
         ('confirmed', 'Confirmed'),
         ('in_transit', 'In Transit'),
         ('done', 'Done'),
         ('cancel', 'Cancel')
         ],
        required=True,
        default='draft',
        copy=False,
        track_visibility='onchange',
    )
    departure_move_ids = fields.One2many(
        'stock.move', 'departure_shipment_id', 'Departure Moves',
        readonly=True, copy=False,
    )
    arrival_move_ids = fields.One2many(
        'stock.move', 'arrival_shipment_id', 'Arrival Moves',
        readonly=True, copy=False,
    )
    departure_picking_ids = fields.One2many(
        compute='_get_departure_picking_ids',
        comodel_name='stock.picking',
        string='Departure Pickings',
        readonly=True, copy=False,
    )
    arrival_picking_ids = fields.One2many(
        compute='_get_arrival_picking_ids',
        comodel_name='stock.picking',
        string='Arrival Pickings',
        readonly=True, copy=False,
    )
    volume = fields.Float(
        compute='_compute_volume',
        readonly=True,
        store=True,
    )
    weight = fields.Float(
        compute='_compute_weights',
        readonly=True,
        store=True,
    )
    weight_net = fields.Float(
        compute='_compute_weights',
        readonly=True,
    )
    departure_picking_count = fields.Integer(
        compute='_departure_picking_count',
    )
    arrival_picking_count = fields.Integer(
        compute='_arrival_picking_count',
    )

    @api.one
    @api.constrains('initial_etd', 'initial_eta')
    def _check_initial_estimated_times(self):
        if (self.initial_etd and self.initial_eta and
                self.initial_etd > self.initial_eta):
            raise exceptions.ValidationError(
                _('Initial ETD cannot be set after initial ETA.'))

    @api.one
    @api.constrains('etd', 'eta')
    def _check_estimated_times(self):
        if self.etd and self.eta and self.etd > self.eta:
            raise exceptions.ValidationError(
                _('ETD cannot be set after ETA.'))

    @api.multi
    def _get_related_picking(self, direction):
        cr = self.env.cr
        picking_ids = {}
        for shipment in self:
            picking_ids[shipment.id] = []
        rel_field = "sm.%s_shipment_id" % direction
        sql = ("SELECT DISTINCT %(rel)s, sm.picking_id "
               "FROM stock_move sm "
               "WHERE %(rel)s IN %%s AND sm.picking_id is NOT NULL"
               % {'rel': rel_field})
        cr.execute(sql, (tuple(self.ids),))
        res = cr.fetchall()
        for line in res:
            picking_ids[line[0]].append(line[1])
        return picking_ids

    @api.multi
    def _get_departure_picking_ids(self):
        pickings = self._get_related_picking('departure')
        for shipment in self:
            # Must set None or will try to access it before being computed
            shipment.departure_picking_ids = None
            shipment.departure_picking_ids = [(6, 0, pickings[shipment.id])]

    @api.multi
    def _get_arrival_picking_ids(self):
        pickings = self._get_related_picking('arrival')
        for shipment in self:
            # Must set None or will try to access it before being computed
            shipment.arrival_picking_ids = None
            shipment.arrival_picking_ids = [(6, 0, pickings[shipment.id])]

    @api.one
    @api.depends('departure_move_ids.product_qty',
                 'departure_move_ids.product_id.volume')
    def _compute_volume(self):
        volume = 0.0
        for move in self.departure_move_ids:
            volume += move.product_qty * move.product_id.volume
        self.volume = volume

    @api.one
    @api.depends('departure_move_ids.weight',
                 'departure_move_ids.weight_net')
    def _compute_weights(self):
        weight = 0
        weight_net = 0
        for move in self.departure_move_ids:
            weight += move.weight or 0.0
            weight_net += move.weight_net or 0.0
        self.weight = weight
        self.weight_net = weight_net

    _sql_constraints = [
        ('name_uniq',
         'unique(name)',
         'Shipment Plan Reference must be unique'),
    ]

    @api.model
    def create(self, values):
        if values.get('name', '/') == '/':
            seq_obj = self.env['ir.sequence']
            values['name'] = seq_obj.get('shipment.plan') or '/'
        return super(ShipmentPlan, self).create(values)

    @api.multi
    def action_cancel_draft(self):
        self.write({'state': 'draft'})
        self.delete_workflow()
        self.create_workflow()
        return True

    @api.multi
    def _get_confirmed_departure_moves(self):
        return [m.state == 'done' for m
                in self.mapped('departure_move_ids')]

    @api.multi
    def is_departed(self):
        """
        Check if all departure moves are done
        """
        return all(self._get_confirmed_departure_moves())

    @api.multi
    def has_done_moves(self):
        """
        Check if at least one departure move is done
        """
        return any(self._get_confirmed_departure_moves())

    @api.multi
    def action_cancel(self):
        if self.has_done_moves():
            raise exceptions.Warning(
                _("You cannot cancel a shipment plan with done moves"))
        # Free all related moves
        self.departure_move_ids.write({'departure_shipment_id': False})
        self.arrival_move_ids.write({'arrival_shipment_id': False})
        self.write({'state': 'cancel'})
        return True

    @api.multi
    def action_confirm(self):
        self.write({'state': 'confirmed'})
        return True

    @api.multi
    def _popup_to_transit_confirm(self):
        ctx = {'active_id': self.id, 'active_ids': self.ids,
               'active_model': self._name}
        wiz_model = self.env['shipment.transit.confirm']
        wiz = wiz_model.with_context(ctx).create({})
        return wiz.action_open_window()

    @api.multi
    def button_action_transit(self):
        if not self.has_done_moves():
            raise exceptions.Warning(
                _("You cannot send to transit a shipment plan without any "
                  "done moves"))
        if not self.is_departed():
            return self._popup_to_transit_confirm()
        return self.signal_workflow('transit_start')

    @api.multi
    def action_transit(self):
        self.write({'state': 'in_transit'})
        return True

    @api.multi
    def action_done(self):
        now = time.strftime(DT_FORMAT)
        self.write({'state': 'done', 'date_end': now})
        return True

    @api.multi
    def action_view_departure_picking(self):
        self.ensure_one()
        pickings = self.departure_picking_ids
        if not pickings:
            return False
        ref = 'stock_shipment_management.shipment_open_picking'
        action_dict = self.env.ref(ref).read()[0]
        action_dict['domain'] = [('id', 'in', pickings.ids)]
        return action_dict

    @api.multi
    def action_view_arrival_picking(self):
        self.ensure_one()
        pickings = self.arrival_picking_ids
        if not pickings:
            return False
        ref = 'stock_shipment_management.shipment_open_picking'
        action_dict = self.env.ref(ref).read()[0]
        action_dict['domain'] = [('id', 'in', pickings.ids)]
        return action_dict

    @api.multi
    def is_transit_done(self):
        for move in self.arrival_move_ids:
            if move.state not in ('done', 'cancel'):
                return False
        else:
            return True

    @api.multi
    @api.depends('departure_picking_ids')
    def _departure_picking_count(self):
        self.ensure_one()
        self.departure_picking_count = len(self.departure_picking_ids)

    @api.multi
    @api.depends('arrival_picking_ids')
    def _arrival_picking_count(self):
        self.ensure_one()
        self.arrival_picking_count = len(self.arrival_picking_ids)
