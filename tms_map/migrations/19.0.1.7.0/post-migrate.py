# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def migrate(cr, version):
    """Keep contacts that already have coordinates visible as a point."""
    cr.execute(
        """
        UPDATE res_partner
           SET tms_map_shape = 'point'
         WHERE tms_map_shape IS NULL
           AND (
                COALESCE(partner_latitude, 0) != 0
                OR COALESCE(partner_longitude, 0) != 0
           )
        """
    )
