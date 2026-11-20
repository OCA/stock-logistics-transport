# Copyright 2026 ACSONE SA/NV (https://acsone.eu)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import Command
from odoo.upgrade import util


def migrate(cr, version):
    if not version or not util.table_exists(cr, "shipment_advice_legacy_picking_order"):
        return

    if not util.module_installed(cr, "shipment_advice_partner_sorting"):
        raise RuntimeError("Shipment advice partner sorting was not installed")

    env = util.env(cr)
    cr.execute(
        """
        SELECT old_order.shipment_advice_id, picking.partner_id,
               CASE picking_type.code
                   WHEN 'incoming' THEN 'pickup'
                   WHEN 'outgoing' THEN 'delivery'
               END AS operation_type,
               (array_agg(old_order.sequence ORDER BY old_order.sequence NULLS LAST,
                                                    old_order.id))[1],
               array_agg(DISTINCT picking.id ORDER BY picking.id)
          FROM shipment_advice_legacy_picking_order old_order
          JOIN shipment_advice advice ON advice.id = old_order.shipment_advice_id
          JOIN stock_picking picking ON picking.id = old_order.stock_picking_id
          JOIN stock_picking_type picking_type ON picking_type.id = picking.picking_type_id
         WHERE advice.partner_sorting_enabled IS TRUE
         GROUP BY old_order.shipment_advice_id, picking.partner_id, operation_type
         ORDER BY old_order.shipment_advice_id, picking.partner_id NULLS LAST, operation_type
        """
    )
    groups = cr.fetchall()
    order_model = env["shipment.advice.planned.partner.order"]
    for advice_id, partner_id, operation_type, sequence, picking_ids in groups:
        orders = order_model.search(
            [
                ("shipment_advice_id", "=", advice_id),
                ("partner_id", "=", partner_id or False),
                ("operation_type", "=", operation_type or False),
            ]
        )
        if orders:
            orders.write(
                {
                    "sequence": sequence or 0,
                    "stock_picking_ids": [Command.link(pid) for pid in picking_ids],
                }
            )
        else:
            order_model.create(
                {
                    "shipment_advice_id": advice_id,
                    "partner_id": partner_id or False,
                    "operation_type": operation_type or False,
                    "sequence": sequence or 0,
                    "stock_picking_ids": [Command.set(picking_ids)],
                }
            )
    env.flush_all()
