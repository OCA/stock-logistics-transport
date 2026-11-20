import logging

from odoo.tools.parse_version import parse_version
from odoo.upgrade import util

_logger = logging.getLogger(__name__)


def _prepare_legacy_ranks(cr):
    if not util.column_exists(cr, "stock_picking", "toursolver_shipment_advice_rank"):
        raise RuntimeError("The historical TourSolver rank column is missing")

    if util.table_exists(cr, "shipment_advice_legacy_picking_order"):
        cr.execute(
            """
            UPDATE shipment_advice_legacy_picking_order old_order
               SET sequence = picking.toursolver_shipment_advice_rank
              FROM stock_picking picking
             WHERE old_order.shipment_advice_id = picking.planned_shipment_advice_id
               AND old_order.stock_picking_id = picking.id
               AND picking.toursolver_shipment_advice_rank IS NOT NULL
            """
        )
        cr.execute(
            """
            INSERT INTO shipment_advice_legacy_picking_order (
                shipment_advice_id, stock_picking_id, sequence, company_id,
                create_uid, create_date, write_uid, write_date
            )
            SELECT advice.id, picking.id, picking.toursolver_shipment_advice_rank,
                   advice.company_id, advice.create_uid, advice.create_date,
                   advice.write_uid, advice.write_date
              FROM stock_picking picking
              JOIN shipment_advice advice
                ON advice.id = picking.planned_shipment_advice_id
             WHERE picking.toursolver_shipment_advice_rank IS NOT NULL
               AND NOT EXISTS (
                   SELECT 1 FROM shipment_advice_legacy_picking_order old_order
                    WHERE old_order.shipment_advice_id = advice.id
                      AND old_order.stock_picking_id = picking.id
               )
            """
        )
    cr.execute(
        """
        UPDATE shipment_advice advice
           SET partner_sorting_enabled = TRUE
         WHERE advice.shipment_type = 'outgoing'
           AND EXISTS (
               SELECT 1
                 FROM stock_picking ranked_picking
                WHERE ranked_picking.planned_shipment_advice_id = advice.id
                  AND ranked_picking.toursolver_shipment_advice_rank IS NOT NULL
           )
           AND EXISTS (
               SELECT 1
                 FROM stock_move move
                 JOIN stock_picking picking ON picking.id = move.picking_id
                WHERE move.shipment_advice_id = advice.id
                GROUP BY move.shipment_advice_id
               HAVING COUNT(DISTINCT COALESCE(picking.partner_id, 0)) > 1
           )
        """
    )
    util.env(cr).invalidate_all()


def migrate(cr, version):
    if not version:
        return

    migrate_ranks = parse_version(version) < parse_version("16.0.3.3.0")
    if migrate_ranks:
        # We maintain the legacy ranks as it was done in migrations of
        # shipment_advice_partner_sorting...
        _prepare_legacy_ranks(cr)
    cr.execute(
        """
        SELECT DISTINCT advice.id
          FROM shipment_advice advice
          JOIN shipment_advice_planned_partner_order partner_order
            ON partner_order.shipment_advice_id = advice.id
         WHERE advice.shipment_type = 'outgoing'
           AND advice.partner_sorting_enabled IS TRUE
           AND partner_order.operation_type IS NULL
        """
    )
    ids = {row[0] for row in cr.fetchall()}
    if migrate_ranks:
        cr.execute(
            """
            SELECT DISTINCT advice.id
              FROM shipment_advice advice
              JOIN stock_picking picking
                ON picking.planned_shipment_advice_id = advice.id
             WHERE advice.shipment_type = 'outgoing'
               AND advice.partner_sorting_enabled IS TRUE
               AND picking.toursolver_shipment_advice_rank IS NOT NULL
            """
        )
        ids.update(row[0] for row in cr.fetchall())
    if ids:
        util.recompute_fields(
            cr,
            "shipment.advice",
            ["planned_partner_order_ids"],
            ids=sorted(ids),
            logger=_logger,
            strategy="flush",
        )

    if not migrate_ranks:
        return

    env = util.env(cr)
    env.flush_all()
    cr.execute(
        """
        UPDATE shipment_advice_planned_partner_order partner_order
           SET sequence = ranks.sequence
          FROM (
              SELECT advice.id AS advice_id, picking.partner_id,
                     CASE picking_type.code
                         WHEN 'incoming' THEN 'pickup'
                         WHEN 'outgoing' THEN 'delivery'
                     END AS operation_type,
                     MIN(picking.toursolver_shipment_advice_rank) AS sequence
                FROM stock_picking picking
                JOIN shipment_advice advice
                  ON advice.id = picking.planned_shipment_advice_id
                JOIN stock_picking_type picking_type
                  ON picking_type.id = picking.picking_type_id
               WHERE advice.shipment_type = 'outgoing'
                 AND advice.partner_sorting_enabled IS TRUE
                 AND picking.toursolver_shipment_advice_rank IS NOT NULL
               GROUP BY advice.id, picking.partner_id, operation_type
          ) ranks
         WHERE partner_order.shipment_advice_id = ranks.advice_id
           AND partner_order.partner_id IS NOT DISTINCT FROM ranks.partner_id
           AND partner_order.operation_type IS NOT DISTINCT FROM ranks.operation_type
        """
    )
    env["shipment.advice.planned.partner.order"].invalidate_model(["sequence"])
