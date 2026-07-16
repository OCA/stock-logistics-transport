from odoo import fields, models


class TMSTeam(models.Model):
    _inherit = "tms.team"

    allowed_vehicle_type_ids = fields.Many2many(
        "fleet.vehicle.type",
        string="Allowed Vehicle Types",
        help="Types of vehicles allowed in this team",
    )
    default_depot_location_id = fields.Many2one(
        "res.partner",
        string="Default Depot Location",
        help="Default depot/starting point for this team",
    )
