from odoo import fields, models


class FleetVehicleModel(models.Model):
    _inherit = "fleet.vehicle.model"

    vehicle_type_id = fields.Many2one(
        "fleet.vehicle.type",
        string="TMS Vehicle Type",
        help="Type of vehicle (Van, VUC, Toco, etc) for capacity management",
    )
