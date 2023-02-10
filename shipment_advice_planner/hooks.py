# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import logging

from odoo.tools import sql

_logger = logging.getLogger(__name__)


def pre_init_hook(cr):
    """This hook will initialize the computed columns that are added in the
    module. This is required to avoid the compute methods to be called
    by the orm during the module installation."""
    if not sql.column_exists(cr, "stock_picking", "can_be_planned_in_shipment_advice"):
        _logger.info(
            "Creating column can_be_planned_in_shipment_advice into stock_picking"
        )
        cr.execute(
            """
            ALTER TABLE stock_picking ADD COLUMN can_be_planned_in_shipment_advice boolean;
            """
        )
        cr.execute(
            """
            UPDATE stock_picking
            SET can_be_planned_in_shipment_advice = true
            FROM stock_picking_type as spt
            WHERE
                planned_shipment_advice_id is null
                AND state = 'assigned'
                AND spt.id = stock_picking.picking_type_id
                AND spt.code = 'outgoing'
        """
        )
        _logger.info(f"{cr.rowcount} rows updated in stock_picking")
