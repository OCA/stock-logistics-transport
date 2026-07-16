# Copyright (C) 2025 KMEE (https://kmee.com.br)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class TMSOrderStop(models.Model):
    """
    Extend TMS Order Stop with Leaflet map visualization support.

    Uses existing latitude/longitude and display_address fields
    from tms_delivery_stops. No additional fields needed.
    """

    _inherit = "tms.order.stop"
