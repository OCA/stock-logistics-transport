# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def migrate(cr, version):
    """Drop text origin columns so they can be recreated as partners."""
    if not version:
        return
    cr.execute(
        """
        SELECT column_name
          FROM information_schema.columns
         WHERE table_name = 'tms_order'
           AND data_type = 'character varying'
           AND column_name IN ('origin_location', 'destination_location')
        """
    )
    columns = {row[0] for row in cr.fetchall()}
    if "origin_location" in columns:
        cr.execute("ALTER TABLE tms_order DROP COLUMN origin_location")
    if "destination_location" in columns:
        cr.execute("ALTER TABLE tms_order DROP COLUMN destination_location")
