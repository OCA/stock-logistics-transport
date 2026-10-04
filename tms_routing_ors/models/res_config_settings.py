# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    tms_routing_ors_api_key = fields.Char(
        string="OpenRouteService API key",
        config_parameter="tms_routing_ors.api_key",
    )
