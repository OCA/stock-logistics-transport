# Copyright (C) 2018 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # Groups

    group_tms_team = fields.Boolean(
        string="Manage Teams", implied_group="tms.group_tms_team"
    )
    group_tms_crew = fields.Boolean(
        string="Manage Crews", implied_group="tms.group_tms_crew"
    )
    group_tms_driver_license = fields.Boolean(
        string="Manage Driver License", implied_group="tms.group_tms_driver_license"
    )

    group_tms_vehicle_insurance = fields.Boolean(
        string="Manage Vehicle Insurance",
        implied_group="tms.group_tms_vehicle_insurance",
    )

    group_tms_route = fields.Boolean(
        string="Manage Routes", implied_group="tms.group_tms_route"
    )

    group_tms_route_stop = fields.Boolean(
        string="Manage Route Stops", implied_group="tms.group_tms_route_stop"
    )

    group_tms_uom = fields.Boolean(
        string="Units of Measure", implied_group="uom.group_uom"
    )

    # Custom Fields

    driver_license_security_days = fields.Integer(
        required=True,
        string="Driver license security days",
        config_parameter="tms.default_driver_license_security_days",
    )

    vehicle_insurance_security_days = fields.Integer(
        required=True,
        string="Vehicle Insurance security days",
        config_parameter="tms.default_vehicle_insurance_security_days",
    )

    @api.model
    def _length_domain(self):
        return [("category_id.id", "=", self.env.ref("uom.uom_categ_length").id)]

    tms_length_uom = fields.Many2one(
        "uom.uom",
        domain=_length_domain,
        default_model="res.config.settings",
        config_parameter="tms.default_length_uom",
        default=lambda self: self.env.ref("uom.product_uom_meter").id,
    )

    tms_distance_uom = fields.Many2one(
        "uom.uom",
        domain=_length_domain,
        default_model="res.config.settings",
        config_parameter="tms.default_distance_uom",
        default=lambda self: self.env.ref("uom.product_uom_km").id,
    )

    @api.model
    def _weight_domain(self):
        return [("category_id.id", "=", self.env.ref("uom.product_uom_categ_kgm").id)]

    tms_weight_uom = fields.Many2one(
        "uom.uom",
        domain=_weight_domain,
        default_model="res.config.settings",
        config_parameter="tms.default_weight_uom",
        default=lambda self: self.env.ref("uom.product_uom_kgm").id,
    )

    @api.model
    def _speed_domain(self):
        return [("category_id.id", "=", self.env.ref("tms.uom_category_speed").id)]

    tms_speed_uom = fields.Many2one(
        "uom.uom",
        domain=_speed_domain,
        default_model="res.config.settings",
        config_parameter="tms.default_speed_uom",
        default=lambda self: self.env.ref("tms.uom_kmh").id,
    )

    @api.model
    def _time_domain(self):
        return [("category_id.id", "=", self.env.ref("uom.uom_categ_wtime").id)]

    tms_time_uom = fields.Many2one(
        "uom.uom",
        domain=_time_domain,
        default_model="res.config.settings",
        config_parameter="tms.default_time_uom",
        default=lambda self: self.env.ref("uom.product_uom_hour").id,
    )

    # Modules
    module_tms_purchase = fields.Boolean(string="Manage trip purchases")
    module_tms_sale = fields.Boolean(string="Manage trip sales")
    module_tms_account = fields.Boolean(string="Manage trip invoicing")
    module_tms_account_asset = fields.Boolean(
        string="Manage vehicle as accounting assets"
    )
    module_tms_expense = fields.Boolean(string="Manage trip expenses")
