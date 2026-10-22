# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class FleetVehicleModel(models.Model):
    _inherit = "fleet.vehicle.model"

    vehicle_type = fields.Selection(
        selection_add=[
            ("truck", "Truck"),
            ("bus", "Bus"),
            ("boat", "Boat"),
            ("plane", "Plane"),
            ("van", "Van"),
        ],
        ondelete={
            "truck": "set default",
            "bus": "set default",
            "boat": "set default",
            "plane": "set default",
            "van": "set default",
        },
    )
    max_weight_capacity = fields.Float(string="Max Payload / Max Weight Capacity")
    max_weight_uom_id = fields.Many2one(
        "uom.uom",
        string="Weight unit",
        domain=lambda self: self.env["res.config.settings"]._weight_domain(),
        default=lambda self: self._default_weight_uom_id(),
    )
    max_volume_capacity = fields.Float(string="Max Cubic Capacity (Cube)")
    trunk_volume = fields.Float(string="Trunk / Cargo Bay Volume")
    trunk_volume_uom_id = fields.Many2one(
        "uom.uom",
        string="Trunk volume unit",
        domain=lambda self: self.env["res.config.settings"]._volume_domain(),
        default=lambda self: self._default_volume_uom_id(),
    )
    passenger_capacity = fields.Integer(string="Passenger Capacity / Seats")
    belly_volume = fields.Float(string="Belly Compartment Capacity (Volume)")
    belly_volume_uom_id = fields.Many2one(
        "uom.uom",
        string="Belly volume unit",
        domain=lambda self: self.env["res.config.settings"]._volume_domain(),
        default=lambda self: self._default_volume_uom_id(),
    )
    belly_weight = fields.Float(string="Belly Compartment Capacity (Weight)")
    belly_weight_uom_id = fields.Many2one(
        "uom.uom",
        string="Belly weight unit",
        domain=lambda self: self.env["res.config.settings"]._weight_domain(),
        default=lambda self: self._default_weight_uom_id(),
    )
    standing_capacity = fields.Integer(string="Standing Capacity")
    loading_length = fields.Float(string="Linear Feet / Loading Meters")
    loading_length_uom_id = fields.Many2one(
        "uom.uom",
        string="Loading length unit",
        domain=lambda self: self.env["res.config.settings"]._length_domain(),
        default=lambda self: self._default_distance_uom_id(),
    )
    pallet_capacity = fields.Integer(string="Pallet Capacity")
    max_axle_weight = fields.Float(string="Max Axle Weight Limits")
    max_axle_weight_uom_id = fields.Many2one(
        "uom.uom",
        string="Axle weight unit",
        domain=lambda self: self.env["res.config.settings"]._weight_domain(),
        default=lambda self: self._default_weight_uom_id(),
    )
    door_width = fields.Float(string="Door width")
    door_height = fields.Float(string="Door height")
    door_dimension_uom_id = fields.Many2one(
        "uom.uom",
        string="Door dimension unit",
        domain=lambda self: self.env["res.config.settings"]._length_domain(),
        default=lambda self: self._default_distance_uom_id(),
    )
    teu_capacity = fields.Integer(
        string="TEU Capacity (Twenty-foot Equivalent Unit)"
    )
    deadweight_tonnage = fields.Float(
        string="Deadweight Tonnage (DWT)",
        help=(
            "The ship's total cargo capacity, including fuel, water, and crew "
            "(critical for bulk cargo ships)."
        ),
    )
    deadweight_uom_id = fields.Many2one(
        "uom.uom",
        string="Deadweight unit",
        domain=lambda self: self.env["res.config.settings"]._weight_domain(),
        default=lambda self: self._default_weight_uom_id(),
    )
    draft_limit = fields.Float(
        string="Draft Limit (Calado)",
        help=(
            "The maximum depth the ship can sink into the water when fully "
            "loaded (determines whether it can enter certain ports)."
        ),
    )
    draft_uom_id = fields.Many2one(
        "uom.uom",
        string="Draft unit",
        domain=lambda self: self.env["res.config.settings"]._length_domain(),
        default=lambda self: self._default_distance_uom_id(),
    )
    position_slots = fields.Integer(
        string="Position Slots (Main Deck / Lower Deck)",
        help="Number of spaces or locking slots available for air containers.",
    )
    max_takeoff_weight = fields.Float(
        string="Maximum Takeoff Weight (MTOW)",
        help=(
            "Maximum total weight at which the aircraft can take off safely "
            "(varies with weather and airport altitude)."
        ),
    )
    max_takeoff_weight_uom_id = fields.Many2one(
        "uom.uom",
        string="Takeoff weight unit",
        domain=lambda self: self.env["res.config.settings"]._weight_domain(),
        default=lambda self: self._default_weight_uom_id(),
    )
    floor_loading_limit = fields.Float(
        string="Floor Loading Limit / Bearing Limit",
        help=(
            "The maximum weight pressure per square meter (kg/m²) that the "
            "cabin floor can bear."
        ),
    )
    floor_loading_uom_id = fields.Many2one(
        "uom.uom",
        string="Floor loading unit",
        domain=lambda self: self.env["res.config.settings"]._pressure_domain(),
        default=lambda self: self._default_pressure_uom_id(),
    )
    max_volume_uom_id = fields.Many2one(
        "uom.uom",
        string="Volume unit",
        domain=lambda self: self.env["res.config.settings"]._volume_domain(),
        default=lambda self: self._default_volume_uom_id(),
    )

    def _default_weight_uom_id(self):
        return self.env["res.config.settings"]._configured_uom(
            "tms.default_weight_uom", "uom.product_uom_kgm"
        )

    def _default_distance_uom_id(self):
        return self.env["res.config.settings"]._configured_uom(
            "tms.default_distance_uom", "uom.product_uom_km"
        )

    def _default_volume_uom_id(self):
        return self.env["res.config.settings"]._configured_uom(
            "tms.default_volume_uom", "uom.product_uom_cubic_meter"
        )

    def _default_pressure_uom_id(self):
        return self.env.ref("tms.uom_kg_per_m2", raise_if_not_found=False)
