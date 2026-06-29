# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle"

    tms_service_product_id = fields.Many2one(
        "product.product",
        string="TMS Service",
        domain="[('type', '=', 'service'), ('product_tmpl_id.tms_trip', '=', True)]",
    )
    tms_service_filter_type = fields.Char(compute="_compute_tms_service_filter_type")

    @api.depends("operation")
    def _compute_tms_service_filter_type(self):
        mapping = {"passenger": "seat", "cargo": "trip"}
        for vehicle in self:
            vehicle.tms_service_filter_type = mapping.get(vehicle.operation, False)

    @api.onchange("operation")
    def _onchange_operation_tms_service(self):
        for vehicle in self:
            product = vehicle.tms_service_product_id
            if not product:
                continue
            expected_type = vehicle.tms_service_filter_type
            if (
                not expected_type
                or product.product_tmpl_id.trip_product_type != expected_type
            ):
                vehicle.tms_service_product_id = False

    @api.constrains("tms_service_product_id", "operation")
    def _check_tms_service_product_operation(self):
        for vehicle in self:
            product = vehicle.tms_service_product_id
            if not product or not vehicle.operation:
                continue
            trip_type = product.product_tmpl_id.trip_product_type
            if vehicle.operation == "passenger" and trip_type != "seat":
                raise ValidationError(
                    self.env._(
                        "Passenger vehicles must use a seat TMS service product."
                    )
                )
            if vehicle.operation == "cargo" and trip_type != "trip":
                raise ValidationError(
                    self.env._("Cargo vehicles must use a trip TMS service product.")
                )
