# -*- coding: utf-8 -*-
# © 2015 Camptocamp SA - Alexandre Fayolle
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from openerp import models, fields, api


class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    consignee_id = fields.Many2one(
        comodel_name='res.partner',
        string='Consignee',
        domain=[('is_consignee', '=', True)],
        help='The person to whom the shipment is to be delivered'
    )

    delivery_address_id = fields.Many2one(
        comodel_name='res.partner',
        string='Delivery Address',
        help='The final delivery address of the procurement group'
    )

    # this field is used for propagating the origin address in push rules,
    # where there is no information on the procurement.
    origin_address_id = fields.Many2one(
        comodel_name='res.partner',
        string='Origin Address',
        help='the origin address of the shipment'
    )


class ProcurementOrder(models.Model):
    _inherit = 'procurement.order'

    origin_address_id = fields.Many2one(
        comodel_name='res.partner',
        string='Origin Address',
        help='the origin address of the shipment'
    )

    consignee_id = fields.Many2one(
        related='group_id.consignee_id'
    )

    delivery_address_id = fields.Many2one(
        related='group_id.delivery_address_id'
    )

    @api.model
    def _prepare_orderpoint_procurement(self, orderpoint, product_qty):
        _super = super(ProcurementOrder, self)
        res = _super._prepare_orderpoint_procurement(orderpoint, product_qty)
        res.update({'partner_dest_id': orderpoint.warehouse_id.partner_id.id})
        return res
