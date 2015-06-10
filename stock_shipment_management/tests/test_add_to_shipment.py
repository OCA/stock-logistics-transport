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
from openerp.tests import common


class TestAddToShipment(common.TransactionCase):
    """ Test adding moves to an existing shipment
    """

    def test_add_a_move_to_shipment(self):
        """ Try to add a move to an existing shipment

        """
        WizardShipmentCreator = self.env['shipment.plan.creator']
        wiz_ctx = {
            'active_model': 'stock.picking',
            'active_ids': self.new_departure_move.ids,
        }
        wiz = WizardShipmentCreator.with_context(wiz_ctx).create(
            {'shipment_id': self.shipment_id.id})
        wiz.onchange_shipment()
        wiz.action_create_shipment()

        self.assertEqual(self.new_departure_move.departure_shipment_id,
                         self.shipment_id)
        self.assertEqual(self.new_departure_move.delivery_address_id,
                         self.to_address_id)

    def test_add_move_to_shipment_with_other_address(self):
        """ Test adding moves to an existing shipment with different to address
        """
        self.new_departure_move.picking_id.delivery_address_id = self.env.ref(
            'base.res_partner_12')
        WizardShipmentCreator = self.env['shipment.plan.creator']
        wiz_ctx = {
            'active_model': 'stock.picking',
            'active_ids': self.new_departure_move.ids,
        }
        wiz = WizardShipmentCreator.with_context(wiz_ctx).create(
            {'shipment_id': self.shipment_id.id})
        wiz.onchange_shipment()
        wiz.action_create_shipment()

        self.assertEqual(self.new_departure_move.departure_shipment_id,
                         self.shipment_id)
        self.assertEqual(self.new_departure_move.delivery_address_id,
                         self.to_address_id)

    def _create_transit_move(self):
        SO = self.env['sale.order']
        SOL = self.env['sale.order.line']
        product = self.env.ref('product.product_product_33')

        so_vals = {
            'partner_id': self.ref('base.res_partner_1'),
        }

        so = SO.create(so_vals)

        sol_vals = {
            'order_id': so.id,
            'product_id': product.id,
            'name': "[HEAD-USB] Headset USB",
            'product_uom_qty': 42,
            'product_uom': self.ref('product.product_uom_unit'),
            'price_unit': 65,
        }

        SOL.create(sol_vals)
        so.signal_workflow('order_confirm')

        # get move line of single created picking
        dest_move = self.so.picking_ids.move_lines

        # Run procurement
        proc_group = so.picking_ids.group_id
        proc = proc_group.procurement_ids.filtered(
            lambda rec: rec.state == 'confirmed')
        proc.run()

        return self.env['stock.move'].search(
            [('move_dest_id', '=', dest_move.id)])

    def setUp(self):
        """This setup is repeated on a new transaction for every test.
        No need to duplicate test data then.
        """
        super(TestAddToShipment, self).setUp()

        # Set warehouse option to pass shipment by Transit
        warehouse = self.env.ref('stock.warehouse0')
        warehouse.delivery_steps = 'ship_transit'

        old_departure_move = self._create_transit_move()
        self.new_departure_move = self._create_transit_move()

        WizardShipmentCreator = self.env['shipment.plan.creator']
        wiz_ctx = {
            'active_model': 'stock.move',
            'active_ids': old_departure_move.ids,
        }
        wiz = WizardShipmentCreator.with_context(wiz_ctx).create({})
        wiz.action_create_shipment()

        self.shipment = self.departure_move.departure_shipment_id
