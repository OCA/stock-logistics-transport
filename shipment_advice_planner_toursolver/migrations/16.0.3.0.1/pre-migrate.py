import logging

from odoo.tools import sql

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    _logger.info(
        "Rename colmumn partner_defaul_delivery_window_start "
        "to partner_default_delivery_window_start"
    )
    sql.rename_column(
        cr,
        "toursolver_backend",
        "partner_defaul_delivery_window_start",
        "partner_default_delivery_window_start",
    )
