import logging

from odoo.upgrade import util

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    util.explode_execute(
        cr,
        """
                INSERT INTO shipment_advice_planned_picking_order (
                    shipment_advice_id,
                    stock_picking_id,
                    sequence,
                    company_id,
                    create_uid,
                    create_date,
                    write_uid,
                    write_date
                    )
                SELECT
                    shipment_advice.id AS shipment_advice_id,
                    sp.id AS stock_picking_id,
                    sp.toursolver_shipment_advice_rank AS sequence,
                    shipment_advice.company_id AS company_id,
                    shipment_advice.create_uid AS create_uid,
                    shipment_advice.create_date AS create_date,
                    shipment_advice.write_uid AS write_uid,
                    shipment_advice.write_date AS write_date
                FROM
                    shipment_advice
                JOIN stock_picking sp ON sp.planned_shipment_advice_id = shipment_advice.id
                WHERE
                    sp.toursolver_shipment_advice_rank IS NOT NULL
                    AND {parallel_filter}
            """,
        table="shipment_advice",
        logger=_logger,
        bucket_size=1000,
    )
