from odoo.upgrade import util


def migrate(cr, version):
    if not version:
        return
    util.rename_model(
        cr,
        "shipment.advice.planned.picking.order",
        "shipment.advice.planned.partner.order",
        rename_table=False,
    )
    util.rename_table(
        cr,
        "shipment_advice_planned_picking_order",
        "shipment_advice_planned_partner_order",
        remove_constraints=False,
    )
    util.rename_field(
        cr,
        "shipment.advice.planned.partner.order",
        "stock_picking_id",
        "legacy_stock_picking_id",
    )
    util.rename_field(
        cr,
        "shipment.advice",
        "planned_picking_order_ids",
        "planned_partner_order_ids",
    )
    util.rename_field(
        cr,
        "stock.picking",
        "shipment_advice_planned_picking_order_ids",
        "shipment_advice_planned_partner_order_ids",
    )
