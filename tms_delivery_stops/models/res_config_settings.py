from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    tms_default_unloading_time = fields.Float(
        string="Default Unloading Time (minutes)",
        related="company_id.tms_default_unloading_time",
        readonly=False,
        help="Default unloading time in minutes for delivery stops",
    )
    tms_default_origin_location_id = fields.Many2one(
        "res.partner",
        string="Default Origin Location",
        related="company_id.tms_default_origin_location_id",
        readonly=False,
        help="Default origin location for TMS orders",
        domain="[('tms_location', '=', True)]",
        context={"default_tms_location": True},
    )
    tms_default_destination_location_id = fields.Many2one(
        "res.partner",
        string="Default Destination Location",
        related="company_id.tms_default_destination_location_id",
        readonly=False,
        help="Default destination location for TMS orders",
        domain="[('tms_location', '=', True)]",
        context={"default_tms_location": True},
    )
