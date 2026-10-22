# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Recreate stored trip readings as fleet.vehicle.odometer lines."""
    cr.execute("SELECT to_regclass('tms_order_odometer_migration')")
    if not cr.fetchone()[0]:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    cr.execute(
        """
        SELECT order_id, odometer_start, odometer_end
          FROM tms_order_odometer_migration
        """
    )
    for order_id, start, end in cr.fetchall():
        order = env["tms.order"].browse(order_id).exists()
        if not order or not order.vehicle_id:
            _logger.info(
                "Skipping odometer migration for trip %s without a vehicle", order_id
            )
            continue
        if start:
            order.odometer_start = start
        if end:
            order.odometer_end = end
    cr.execute("DROP TABLE tms_order_odometer_migration")
