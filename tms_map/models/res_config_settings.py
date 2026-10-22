from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    group_tms_vehicle_group = fields.Boolean(
        string="Manage Vehicle Groups",
        implied_group="tms_map.group_tms_vehicle_group",
    )
