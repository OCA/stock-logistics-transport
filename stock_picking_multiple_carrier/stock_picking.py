# -*- coding: utf-8 -*-
# © 2016 initOS GmbH
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, fields, api


class StockPickingDelivery(models.Model):

    _name = 'stock.picking.delivery'

    carrier_id = fields.Many2one(
        "delivery.carrier",
        string="Carrier",)
    carrier_tracking_ref = fields.Char(
        string="Carrier Tracking Ref",
        size=32,
        required=True,)
    picking_id = fields.Many2one(
        comodel_name="stock.picking",
        string="Picking",
        required=True)


@api.model
def _carrier_tracking_ref_display(self):
    # use this function with the functional field "carrier_tracking_ref"
    # in StockPicking class
    # to show the carrier information in another module
    # (in sale order for example)
        deliveries = dict([(picking.id, picking.delivery_ids)
                           for picking in self])
        result = {}
        for record_id in self:
            refs = map(lambda delivery:
                       (delivery.carrier_id.name or '') + ': ' +
                       (delivery.carrier_tracking_ref or ''),
                       deliveries[record_id])
            result[record_id] = ', '.join(refs)
        return result


class StockPicking(models.Model):

    _inherit = 'stock.picking'

    delivery_ids = fields.One2many(
        comodel_name="stock.picking.delivery",
        inverse_name="picking_id",
        string="Delivery Information")
    carrier_tracking_ref = fields.Char(
        compute=_carrier_tracking_ref_display,
        string="Carrier Tracking Refs")
