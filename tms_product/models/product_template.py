# Copyright (C) 2024 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

TRANSIT_MODES = [
    ("air", "Air"),
    ("water", "Water"),
    ("road", "Road"),
    ("rail", "Rail"),
]
CARGO_TRANSIT_MODES = [
    ("air", "Air Freight"),
    ("water", "Ocean Freight"),
    ("road", "Road Freight"),
    ("rail", "Rail Freight"),
]
PASSENGER_TRANSIT_MODES = [
    ("air", "Flight"),
    ("water", "Ferry/Cruise"),
    ("road", "Bus"),
    ("rail", "Train"),
]
BOOKING_TYPES = [
    ("shared_space", "Shared space"),
    ("full_asset", "Full asset"),
]
_TRANSIT_VALUES = {value for value, _label in TRANSIT_MODES}
_TRANSIT_GROUPS = {
    "air": "tms.group_tms_air_user",
    "water": "tms.group_tms_water_user",
    "road": "tms.group_tms_road_user",
    "rail": "tms.group_tms_rail_user",
}


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # If it is a vehicle
    tms_vehicle = fields.Boolean(
        string="Is a Vehicle",
        compute="_compute_restore_transport_fields",
        store=True,
        readonly=False,
    )
    vehicle_type = fields.Selection(
        selection="_compute_vehicle_type_selection",
        compute="_compute_restore_vehicle_fields",
        store=True,
        readonly=False,
    )
    model_id = fields.Many2one(
        "fleet.vehicle.model",
        string="Model",
        compute="_compute_restore_vehicle_fields",
        store=True,
        readonly=False,
    )

    transport_type = fields.Selection(
        [
            ("none", "None"),
            ("cargo", "Cargo"),
            ("passenger", "Passenger"),
        ],
        string="Transport Type",
        compute="_compute_restore_transport_fields",
        store=True,
        readonly=False,
    )
    transit_mode = fields.Selection(
        selection="_selection_transit_mode",
        string="Transit mode",
        compute="_compute_restore_transport_line_fields",
        store=True,
        readonly=False,
        help="Air, water, road, or rail network used for this service.",
    )
    transit_mode_cargo = fields.Selection(
        selection="_selection_transit_mode_cargo",
        string="Transit mode",
        compute="_compute_transit_mode_labels",
        inverse="_inverse_transit_mode_cargo",
    )
    transit_mode_passenger = fields.Selection(
        selection="_selection_transit_mode_passenger",
        string="Transit mode",
        compute="_compute_transit_mode_labels",
        inverse="_inverse_transit_mode_passenger",
    )
    booking_type = fields.Selection(
        BOOKING_TYPES,
        string="Booking type",
        compute="_compute_restore_transport_line_fields",
        store=True,
        readonly=False,
        help="Shared space is a seat, cabin, or consolidation. "
        "Full asset is the whole vehicle or an exclusive container.",
    )

    @api.model
    def _allowed_transit_modes(self, modes):
        if self.env.su:
            return modes
        user = self.env.user
        return [
            item
            for item in modes
            if user.has_group(_TRANSIT_GROUPS[item[0]])
        ]

    @api.model
    def _selection_transit_mode(self):
        return self._allowed_transit_modes(TRANSIT_MODES)

    @api.model
    def _selection_transit_mode_cargo(self):
        return self._allowed_transit_modes(CARGO_TRANSIT_MODES)

    @api.model
    def _selection_transit_mode_passenger(self):
        return self._allowed_transit_modes(PASSENGER_TRANSIT_MODES)

    @api.model
    def _compute_vehicle_type_selection(self):
        vehicle_model = self.env["fleet.vehicle.model"]
        vehicle_types = vehicle_model.fields_get(["vehicle_type"])["vehicle_type"][
            "selection"
        ]
        return vehicle_types

    @api.depends("type")
    def _compute_restore_transport_fields(self):
        for product in self:
            if product.type == "service":
                product.tms_vehicle = False
                if product.transport_type not in ("none", "cargo", "passenger"):
                    product.transport_type = "none"
            else:
                product.transport_type = False

    @api.depends("transport_type")
    def _compute_restore_transport_line_fields(self):
        for product in self:
            if product.transport_type in ("cargo", "passenger"):
                mode = product.transit_mode
                product.transit_mode = mode if mode in _TRANSIT_VALUES else False
                booking = product.booking_type
                product.booking_type = (
                    booking if booking in ("shared_space", "full_asset") else False
                )
            else:
                product.transit_mode = False
                product.booking_type = False

    @api.depends("transit_mode")
    def _compute_transit_mode_labels(self):
        for product in self:
            mode = (
                product.transit_mode
                if product.transit_mode in _TRANSIT_VALUES
                else False
            )
            product.transit_mode_cargo = mode
            product.transit_mode_passenger = mode

    def _inverse_transit_mode_cargo(self):
        for product in self:
            if product.transport_type == "cargo":
                product.transit_mode = product.transit_mode_cargo

    def _inverse_transit_mode_passenger(self):
        for product in self:
            if product.transport_type == "passenger":
                product.transit_mode = product.transit_mode_passenger

    @api.onchange("tms_vehicle")
    def _compute_restore_vehicle_fields(self):
        for product in self:
            if product.transport_type not in ("cargo", "passenger"):
                product.vehicle_type = False
                product.model_id = False

    def _prepare_transport_vals(self, vals):
        """Drop the mode that does not belong to the chosen transport type."""
        if "transport_type" not in vals:
            return vals
        vals = dict(vals)
        if vals["transport_type"] not in ("cargo", "passenger"):
            vals["transit_mode"] = False
            vals["booking_type"] = False
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [self._prepare_transport_vals(vals) for vals in vals_list]
        return super().create(vals_list)

    def write(self, vals):
        if "transport_type" in vals:
            vals = self._prepare_transport_vals(vals)
        return super().write(vals)
