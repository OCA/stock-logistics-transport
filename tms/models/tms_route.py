# Copyright (C) 2024 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class TMSRoute(models.Model):
    _name = "tms.route"
    _description = "Transport Management System Route"

    # -------------------------------------
    #                  Fields
    # -------------------------------------

    active = fields.Boolean(default=True)
    name = fields.Char(string="Route Name", required=True)
    origin_location_id = fields.Many2one(
        "res.partner",
        string="Origin Location",
        required=True,
        context={"default_tms_location": True},
    )
    destination_location_id = fields.Many2one(
        "res.partner",
        string="Destination Location",
        required=True,
        context={"default_tms_location": True},
    )

    stop_locations = fields.Boolean(string="Stops locations in route")
    stop_location_ids = fields.Many2many(
        "res.partner",
        string="Stop Locations",
        context={"default_tms_location": True},
    )

    # Route Details
    distance = fields.Float()
    estimated_time = fields.Float()

    distance_uom = fields.Many2one(
        "uom.uom",
        domain="[('category_id', '=', 'Length / Distance')]",
        default=lambda self: self._default_distance_uom_id(),
    )
    estimated_time_uom = fields.Many2one(
        "uom.uom",
        domain="[('category_id', '=', 'Working Time')]",
        default=lambda self: self._default_time_uom_id(),
    )

    # Notes and Comments
    notes = fields.Text(string="Notes/Comments")

    @api.model
    def _default_distance_uom_id(self):
        # Fetch the value of default_distance_uom from settings
        default_distance_uom_id = (
            self.env["ir.config_parameter"].sudo().get_param("tms.default_distance_uom")
        )

        # Return the actual record based on the ID retrieved from settings
        if default_distance_uom_id:
            return self.env["uom.uom"].browse(int(default_distance_uom_id))
        else:
            # If no default_length_uom is set, return None or a default value
            return self.env.ref("uom.product_uom_km", raise_if_not_found=False)

    def _default_time_uom_id(self):
        # Fetch the value of default_time_uom from settings
        default_time_uom_id = (
            self.env["ir.config_parameter"].sudo().get_param("tms.default_time_uom")
        )

        # Return the actual record based on the ID retrieved from settings
        if default_time_uom_id:
            return self.env["uom.uom"].browse(int(default_time_uom_id))
        else:
            # If no default_time_uom is set, return None or a default value
            return self.env.ref("uom.product_uom_hour", raise_if_not_found=False)
