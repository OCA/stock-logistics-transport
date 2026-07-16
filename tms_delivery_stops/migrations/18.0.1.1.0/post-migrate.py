# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Create origin and destination stops for existing orders.

    This migration:
    1. Sets default stop_type='delivery' for all existing stops
    2. Creates origin stops for orders with origin_id
    3. Creates destination stops for orders with destination_id
       (skipped if destination = origin)
    """
    if not version:
        return

    env = api.Environment(cr, SUPERUSER_ID, {})

    _logger.info("Starting migration: Adding endpoint stops to existing orders")

    # Step 1: Set stop_type='delivery' for all existing stops
    # (they don't have stop_type yet)
    cr.execute("""
        UPDATE tms_order_stop
        SET stop_type = 'delivery'
        WHERE stop_type IS NULL
    """)
    _logger.info("Set stop_type='delivery' for existing stops")

    # Step 1.5: Compute stop_type_order for all stops
    cr.execute("""
        UPDATE tms_order_stop
        SET stop_type_order = CASE
            WHEN stop_type = 'origin' THEN 0
            WHEN stop_type = 'delivery' THEN 1
            WHEN stop_type = 'destination' THEN 2
            ELSE 1
        END
        WHERE stop_type_order IS NULL OR stop_type_order != CASE
            WHEN stop_type = 'origin' THEN 0
            WHEN stop_type = 'delivery' THEN 1
            WHEN stop_type = 'destination' THEN 2
            ELSE 1
        END
    """)
    _logger.info("Computed stop_type_order for all stops")

    # Step 2: Find orders that need endpoint stops
    orders = env["tms.order"].search(
        [
            "|",
            ("origin_id", "!=", False),
            ("destination_id", "!=", False),
        ]
    )

    _logger.info(f"Found {len(orders)} orders to process")

    created_origin = 0
    created_destination = 0

    for order in orders:
        # Check existing stop types
        existing_types = set(order.stop_ids.mapped("stop_type"))

        # Create origin stop if needed
        if "origin" not in existing_types and order.origin_id:
            env["tms.order.stop"].create(
                {
                    "order_id": order.id,
                    "stop_type": "origin",
                    "location_id": order.origin_id.id,
                    "sequence": 0,
                    "company_id": order.company_id.id,
                }
            )
            created_origin += 1

        # Create destination stop if needed
        if "destination" not in existing_types and order.destination_id:
            env["tms.order.stop"].create(
                {
                    "order_id": order.id,
                    "stop_type": "destination",
                    "location_id": order.destination_id.id,
                    "sequence": 9999,
                    "company_id": order.company_id.id,
                }
            )
            created_destination += 1

    _logger.info(
        f"Migration complete: created {created_origin} origin stops "
        f"and {created_destination} destination stops"
    )
