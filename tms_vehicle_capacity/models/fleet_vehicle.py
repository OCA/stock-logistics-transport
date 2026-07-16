from odoo import api, fields, models


class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle"

    vehicle_type_id = fields.Many2one(
        "fleet.vehicle.type",
        string="TMS Vehicle Type",
        help="Type of vehicle (Van, VUC, Toco, etc) for capacity management",
    )
    weight_capacity = fields.Float(
        string="Weight Capacity (kg)",
        help="Weight capacity in kilograms",
    )
    weight_capacity_uom_id = fields.Many2one(
        "uom.uom",
        string="Weight Capacity UoM",
        domain=[("category_id.name", "=", "Weight")],
        default=lambda self: self.env["uom.uom"].search([("name", "=", "kg")], limit=1),
    )
    volume_capacity = fields.Float(
        string="Volume Capacity (m³)",
        help="Volume capacity in cubic meters",
    )
    volume_capacity_uom_id = fields.Many2one(
        "uom.uom",
        string="Volume Capacity UoM",
        domain=[("category_id.name", "=", "Volume")],
        default=lambda self: self.env["uom.uom"].search([("name", "=", "m³")], limit=1),
    )
    cost_per_km = fields.Float(
        string="Cost per KM",
        help="Cost per kilometer",
    )
    minimum_trip_cost = fields.Float(
        help="Minimum cost per trip",
    )
    depot_location_id = fields.Many2one(
        "res.partner",
        string="Depot Location",
        help="Default depot/starting point for this vehicle",
    )

    @api.onchange("vehicle_type_id")
    def _onchange_vehicle_type_id(self):
        """Populate capacity and cost fields from vehicle type"""
        if self.vehicle_type_id:
            if not self.weight_capacity:
                self.weight_capacity = self.vehicle_type_id.default_weight_capacity
            if not self.volume_capacity:
                self.volume_capacity = self.vehicle_type_id.default_volume_capacity
            if not self.cost_per_km:
                self.cost_per_km = self.vehicle_type_id.default_cost_per_km
            if not self.minimum_trip_cost:
                self.minimum_trip_cost = self.vehicle_type_id.default_minimum_trip_cost
