from odoo import fields, models


class TMSTeam(models.Model):
    _inherit = "tms.team"

    default_origin_location_id = fields.Many2one(
        "res.partner",
        string="Default Origin Location",
        help=(
            "Default origin location for this team. "
            "If not set, uses the system default."
        ),
        domain="[('tms_location', '=', True)]",
        context={"default_tms_location": True},
    )
    default_destination_location_id = fields.Many2one(
        "res.partner",
        string="Default Destination Location",
        help=(
            "Default destination location for this team. "
            "If not set, uses the system default."
        ),
        domain="[('tms_location', '=', True)]",
        context={"default_tms_location": True},
    )
