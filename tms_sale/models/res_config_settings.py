# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    tms_rate_exchange_date = fields.Selection(
        selection=[
            ("shipment", "Shipment date"),
            ("order", "Order date"),
        ],
        string="Exchange rate date",
        default="shipment",
        config_parameter="tms_sale.rate_exchange_date",
        help="Shipment date converts the rate card with the rate of the "
        "departure day. Order date freezes that rate when the sales order "
        "is confirmed.",
    )
