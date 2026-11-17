# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def migrate(cr, version):
    """Keep trip odometer floats before those columns become Fleet readings."""
    if not version:
        return
    cr.execute(
        """
        SELECT column_name
          FROM information_schema.columns
         WHERE table_name = 'tms_order'
           AND column_name IN ('odometer_start', 'odometer_end')
        """
    )
    columns = {row[0] for row in cr.fetchall()}
    if "odometer_start" not in columns or "odometer_end" not in columns:
        return
    cr.execute(
        """
        CREATE TABLE IF NOT EXISTS tms_order_odometer_migration (
            order_id integer PRIMARY KEY,
            odometer_start double precision,
            odometer_end double precision
        )
        """
    )
    cr.execute(
        """
        INSERT INTO tms_order_odometer_migration (
            order_id, odometer_start, odometer_end
        )
        SELECT id,
               COALESCE(odometer_start, 0),
               COALESCE(odometer_end, 0)
          FROM tms_order
         WHERE COALESCE(odometer_start, 0) <> 0
            OR COALESCE(odometer_end, 0) <> 0
        ON CONFLICT (order_id) DO NOTHING
        """
    )
