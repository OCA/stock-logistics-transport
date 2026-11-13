import logging

from odoo.upgrade import util

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    query = """
        UPDATE shipment_advice_planned_partner_order
        SET operation_type = 'delivery'
        FROM shipment_advice
        WHERE shipment_advice_planned_partner_order.shipment_advice_id
                = shipment_advice.id
            AND shipment_advice.shipment_type = 'outgoing'
            AND {parallel_filter}
    """
    util.explode_execute(
        cr,
        query,
        table="shipment_advice_planned_partner_order",
        logger=_logger,
        bucket_size=1000,
    )
