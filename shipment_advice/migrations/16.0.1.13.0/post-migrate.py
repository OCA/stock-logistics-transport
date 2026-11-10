def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        CREATE TEMP TABLE shipment_advice_planned_partner_order_migration
        ON COMMIT DROP AS
        SELECT
            planned_order.id,
            planned_order.shipment_advice_id,
            planned_order.sequence,
            picking.id AS stock_picking_id,
            picking.partner_id,
            FIRST_VALUE(planned_order.id) OVER (
                PARTITION BY
                    planned_order.shipment_advice_id,
                    picking.partner_id,
                    CASE WHEN picking.partner_id IS NULL THEN picking.id END
                ORDER BY planned_order.sequence, planned_order.id
            ) AS canonical_id
        FROM shipment_advice_planned_partner_order planned_order
        JOIN stock_picking picking
            ON picking.id = planned_order.legacy_stock_picking_id
        """
    )
    cr.execute(
        """
        DELETE FROM shipment_advice_planned_partner_order planned_order
        USING shipment_advice_planned_partner_order_migration migration
        WHERE planned_order.id = migration.id
            AND planned_order.id != migration.canonical_id
        """
    )
    cr.execute(
        """
        UPDATE shipment_advice_planned_partner_order planned_order
        SET partner_id = migration.partner_id
        FROM shipment_advice_planned_partner_order_migration migration
        WHERE planned_order.id = migration.canonical_id
            AND migration.id = migration.canonical_id
        """
    )
    cr.execute(
        """
        INSERT INTO shipment_advice_planned_partner_order_stock_picking_rel (
            shipment_advice_planned_partner_order_id,
            stock_picking_id
        )
        SELECT DISTINCT
            canonical_id,
            stock_picking_id
        FROM shipment_advice_planned_partner_order_migration
        ON CONFLICT DO NOTHING
        """
    )
    cr.execute(
        """
        ALTER TABLE shipment_advice_planned_partner_order
        DROP COLUMN legacy_stock_picking_id
        """
    )
