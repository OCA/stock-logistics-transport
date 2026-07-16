from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    tms_default_unloading_time = fields.Float(
        string="Default Unloading Time (minutes)",
        default=30.0,
        help="Default unloading time in minutes for delivery stops",
    )
    tms_default_origin_location_id = fields.Many2one(
        "res.partner",
        string="Default Origin Location",
        help="Default origin location for TMS orders",
        domain="[('tms_location', '=', True)]",
        context={"default_tms_location": True},
    )
    tms_default_destination_location_id = fields.Many2one(
        "res.partner",
        string="Default Destination Location",
        help="Default destination location for TMS orders",
        domain="[('tms_location', '=', True)]",
        context={"default_tms_location": True},
    )
