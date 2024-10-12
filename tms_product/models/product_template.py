# Copyright (C) 2024 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


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

    # If it is a trip
    tms_trip = fields.Boolean(
        string="Is a trip service",
        compute="_compute_restore_transport_fields",
        store=True,
        readonly=False,
    )
    trip_product_type = fields.Selection(
        [
            ("trip", "New trip"),
            ("seat", "Seat"),
        ],
        default="trip",
        help="Determines if the product is sold as a trip or as a passenger seat",
        compute="_compute_restore_transport_line_fields",
        store=True,
        readonly=False,
    )
    tms_factor_type = fields.Selection(
        [
            ("distance", "Distance"),
            ("weight", "Weight"),
        ],
        default="distance",
        help="""Determines how the trip will be invoiced to the customer:
        - Distance: By the amount of distance traveled
        - Weight: By the amount of weight transported""",
        compute="_compute_restore_transport_line_fields",
        store=True,
        readonly=False,
    )
    tms_factor_distance_uom = fields.Many2one(
        "uom.uom",
        domain=lambda self: [
            ("category_id", "=", self.env.ref("uom.uom_categ_length").id)
        ],
        string="Distance Unit of Measure",
        compute="_compute_restore_transport_line_fields",
        store=True,
        readonly=False,
    )
    tms_factor_weight_uom = fields.Many2one(
        "uom.uom",
        domain=lambda self: [
            ("category_id", "=", self.env.ref("uom.product_uom_categ_kgm").id)
        ],
        string="Weight Unit of Measure",
        compute="_compute_restore_transport_line_fields",
        store=True,
        readonly=False,
    )

    @api.model
    def _compute_vehicle_type_selection(self):
        vehicle_model = self.env["fleet.vehicle.model"]
        vehicle_types = vehicle_model.fields_get(["vehicle_type"])["vehicle_type"][
            "selection"
        ]
        return vehicle_types

    @api.depends("detailed_type")
    def _compute_restore_transport_fields(self):
        for product in self:
            if product.detailed_type in ["service"]:
                product.tms_vehicle = False
            else:
                product.tms_trip = False

    @api.depends("tms_trip")
    def _compute_restore_transport_line_fields(self):
        for product in self:
            if not product.tms_trip:
                product.trip_product_type = False
                product.tms_factor_type = False
                product.tms_factor_distance_uom = False
                product.tms_factor_weight_uom = False

    @api.onchange("tms_vehicle")
    def _compute_restore_vehicle_fields(self):
        for product in self:
            if not product.tms_trip:
                product.vehicle_type = False
                product.model_id = False
