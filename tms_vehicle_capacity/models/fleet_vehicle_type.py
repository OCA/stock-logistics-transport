from odoo import fields, models


class FleetVehicleType(models.Model):
    _name = "fleet.vehicle.type"
    _description = "Fleet Vehicle Type"

    name = fields.Char(
        string="Type Name",
        required=True,
    )
    code = fields.Char(
        required=True,
    )
    description = fields.Text()
    default_weight_capacity = fields.Float(
        string="Default Weight Capacity (kg)",
        help="Default weight capacity in kilograms",
    )
    default_volume_capacity = fields.Float(
        string="Default Volume Capacity (m³)",
        help="Default volume capacity in cubic meters",
    )
    default_cost_per_km = fields.Float(
        string="Default Cost per KM",
        help="Default cost per kilometer",
    )
    default_minimum_trip_cost = fields.Float(
        help="Default minimum cost per trip",
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
    )
    active = fields.Boolean(
        default=True,
    )

    _sql_constraints = [
        ("code_unique", "unique(code)", "Vehicle type code must be unique"),
    ]
