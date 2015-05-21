# -*- coding: utf-8 -*-
#
#
#    Author: Yannick Vaucher
#    Copyright 2014 Camptocamp SA
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
from openerp import models, fields, api, exceptions
from openerp.tools.translate import _


class PurchaseRequisition(models.Model):
    _inherit = "purchase.requisition"

    dest_address_id = fields.Many2one(
        'res.partner',
        'Delivery Address')
    consignee_id = fields.Many2one(
        'res.partner',
        'Consignee',
        domain=[('is_consignee', '=', True)],
        help="The person to whom the shipment is to be delivered.")

    @api.model
    def _prepare_purchase_order(self, requisition, supplier):
        values = super(PurchaseRequisition, self
                       )._prepare_purchase_order(requisition, supplier)

        values['origin_address_id'] = values.get('partner_id')
        values['dest_address_id'] = requisition.dest_address_id.id
        values['consignee_id'] = requisition.consignee_id.id
        return values

    @api.onchange('dest_address_id')
    def onchange_dest_address_id(self):
        """Find a picking type from the address.

        There is a similar onchange in the module
        purchase_requisition_delivery_address. A similar logic to choose the
        picking type is used in the module framework_agreement_sourcing in
        github.com/OCA/vertical-ngo.

        """
        if not self.dest_address_id:
            return

        PickType = self.env['stock.picking.type']
        types = PickType.search([
            ('warehouse_id.partner_id', '=', self.dest_address_id.id),
            ('code', '=', 'incoming'),
        ])

        if types:
            if self.picking_type_id in types:
                return
            picking_type_id = types[0].id
        elif self.dest_address_id.customer:
            # if destination is not for a warehouse address,
            # we set dropshipping picking type
            ref = 'stock_dropshipping.picking_type_dropship'
            picking_type_id = self.env.ref(ref)
        else:
            raise exceptions.Warning(
                _('The delivery address %s is not the address of a '
                  'warehouse or the address of a customer.') %
                self.dest_address_id.name)
        self.picking_type_id = picking_type_id

    @api.onchange('picking_type_id')
    def onchange_picking_type_id(self):
        """If the picking type has an address, use it.

        We cannot empty the address if one is not found, because that gives a
        short circuit with the onchange of the address.

        """
        if self.picking_type_id:
            pick_type = self.picking_type_id

            if pick_type.warehouse_id.partner_id:
                self.dest_address_id = pick_type.warehouse_id.partner_id.id
