# Copyright (C) 2024 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class TMSOrder(models.Model):
    _name = "tms.order"
    _description = "Transport Management System Order"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    active = fields.Boolean(default=True)

    name = fields.Char(
        required=True,
        copy=False,
        readonly=False,
        index="trigram",
        default=lambda self: _("New"),
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        index=True,
        default=lambda self: self.env.company,
        help="Company related to this order",
    )

    description = fields.Text()
    sequence = fields.Integer(default=10)

    route = fields.Boolean(string="Use predefined route")
    route_id = fields.Many2one("tms.route")
    route_origin = fields.Char(related="route_id.origin_location_id.display_name")
    route_destination = fields.Char(
        related="route_id.destination_location_id.display_name"
    )

    origin_id = fields.Many2one(
        "res.partner",
        domain="[('tms_type', '=', 'location')]",
        context={"default_tms_type": "location"},
    )
    destination_id = fields.Many2one(
        "res.partner",
        domain="[('tms_type', '=', 'location')]",
        context={"default_tms_type": "location"},
    )

    origin_location = fields.Char(string="Origin")
    destination_location = fields.Char(string="Destination")

    driver_id = fields.Many2one(
        "res.partner",
        string="Driver",
        context={"default_tms_type": "driver"},
    )
    vehicle_id = fields.Many2one("fleet.vehicle", string="Vehicle")
    tms_team_id = fields.Many2one("tms.team", string="Team")
    crew_id = fields.Many2one("tms.crew", string="Crew")

    stage_id = fields.Many2one(
        "tms.stage",
        string="Stage",
        index=True,
        copy=False,
        domain="[('stage_type', '=', 'order')]",
        default=lambda self: self._default_stage_id(),
        group_expand="_read_group_stage_ids",
        ondelete="set null",
    )

    scheduled_date_start = fields.Datetime(
        string="Scheduled Start", default=datetime.now()
    )
    scheduled_duration = fields.Float(
        help="Scheduled duration of the work in" " hours",
    )
    scheduled_date_end = fields.Datetime(string="Scheduled End")

    start_trip = fields.Boolean(readonly=True)
    end_trip = fields.Boolean(readonly=True)
    date_start = fields.Datetime()
    date_end = fields.Datetime()
    duration = fields.Float(string="Trip Duration")

    diff_duration = fields.Float(
        readonly=True, string="Scheduled Duration - Actual Duration"
    )

    time_uom = fields.Many2one(
        "uom.uom",
        domain="[('category_id', '=', 'Working Time')]",
        default=lambda self: self._default_time_uom_id(),
    )

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

    def _default_stage_id(self):
        stage = self.env["tms.stage"].search(
            [
                ("stage_type", "=", "order"),
            ],
            order="sequence asc",
            limit=1,
        )
        if stage:
            return stage
        raise ValidationError(_("You must create an TMS order stage first."))

    @api.onchange("route")
    def _onchange_route(self):
        if self.route:
            self.origin_id = None
            self.destination_id = None
        else:
            self.route_id = None

    @api.onchange("route_id")
    def _onchange_route_id(self):
        if self.route:
            if self.route_id.estimated_time_uom.name == "Days":
                self.scheduled_duration = self.route_id.estimated_time * 24
            else:
                self.scheduled_duration = self.route_id.estimated_time
        else:
            self.scheduled_duration = 0.0

    @api.onchange("scheduled_duration")
    def _onchange_scheduled_duration(self):
        if self.scheduled_date_start:
            self.scheduled_date_end = self.scheduled_date_start + timedelta(
                hours=self.scheduled_duration
            )

    @api.onchange("scheduled_date_end")
    def _onchange_scheduled_date_end(self):
        if self.scheduled_date_end and self.scheduled_date_start:
            difference = self.scheduled_date_end - self.scheduled_date_start
            self.scheduled_duration = difference.total_seconds() / 3600

    @api.onchange("scheduled_date_start")
    def _onchange_scheduled_date_start(self):
        if self.scheduled_date_start:
            self.scheduled_date_end = self.scheduled_date_start + timedelta(
                hours=self.scheduled_duration
            )

    @api.onchange("duration")
    def _onchange_duration(self):
        if self.date_start:
            self.date_end = self.date_start + timedelta(hours=self.duration)

    @api.onchange("date_end")
    def _onchange_date_end(self):
        if self.date_end and self.date_start:
            difference = self.date_end - self.date_start
            self.duration = difference.total_seconds() / 3600

    @api.onchange("date_start")
    def _onchange_date_start(self):
        if self.date_start:
            self.date_end = self.date_start + timedelta(hours=self.duration)

    @api.depends("tms_team_id.driver_ids", "crew_id.driver_ids")
    def _compute_driver_ids_domain(self):
        all_drivers = self.env["res.partner"].search([("tms_type", "=", "driver")])
        all_driver_ids = all_drivers.ids
        for order in self:
            order.driver_ids_domain = [(6, 0, all_driver_ids)]
            if order.tms_team_id:
                order.driver_ids_domain = [(6, 0, order.tms_team_id.driver_ids.ids)]
            if order.crew_id:
                order.driver_ids_domain = [(6, 0, order.crew_id.driver_ids.ids)]

    driver_ids_domain = fields.Many2many(
        "res.partner",
        "team_drivers_rel",
        compute="_compute_driver_ids_domain",
        default=lambda self: self.env["res.partner"]
        .search([("tms_type", "=", "driver")])
        .ids,
    )

    @api.depends("tms_team_id")
    def _compute_vehicle_ids_domain(self):
        all_vehicles = self.env["fleet.vehicle"].search([])
        all_vehicles_ids = all_vehicles.ids
        for order in self:
            order.vehicle_ids_domain = [(6, 0, all_vehicles_ids)]
            if order.tms_team_id:
                order.vehicle_ids_domain = [(6, 0, order.tms_team_id.vehicle_ids.ids)]

    vehicle_ids_domain = fields.Many2many(
        "fleet.vehicle",
        "team_vehicles_rel",
        compute="_compute_vehicle_ids_domain",
        default=lambda self: self.env["fleet.vehicle"].search([]).ids,
    )

    @api.depends("tms_team_id")
    def _compute_crew_ids_domain(self):
        all_crews = self.env["tms.crew"].search([])
        all_crews_ids = all_crews.ids

        if self.tms_team_id:
            self.crew_ids_domain = [(6, 0, self.tms_team_id.crew_ids.ids)]
        else:
            self.crew_ids_domain = [(6, 0, all_crews_ids)]

    crew_ids_domain = fields.Many2many(
        "tms.crew",
        "team_crews_rel",
        compute="_compute_crew_ids_domain",
        default=lambda self: self.env["tms.crew"].search([]).ids,
    )

    @api.depends("crew_id")
    def _compute_active_crew(self):
        for order in self:
            order.crew_active = bool(order.crew_id)
            if order.crew_id:
                order.vehicle_id = order.crew_id.default_vehicle_id.id
            else:
                order.vehicle_id = order.vehicle_id

    crew_active = fields.Boolean(compute="_compute_active_crew")

    # Constraints
    _sql_constraints = [
        ("name_uniq", "unique (name)", "Trip name already exists!"),
        (
            "duration_ge_zero",
            "CHECK (scheduled_duration >= 0)",
            "Scheduled duration must be greater than or equal to zero!",
        ),
    ]

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        return self.env["tms.stage"].search([("stage_type", "=", "order")], order=order)

    def button_start_order(self):
        # Check the vehicle insurance
        vehicle_security_days = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("tms.default_vehicle_insurance_security_days")
        )
        if vehicle_security_days and self.vehicle_id.insurance_id:
            insurance_id = self.vehicle_id.insurance_id
            days_to_expire = (insurance_id.end_date - datetime.today().date()).days

            if days_to_expire <= vehicle_security_days:
                raise UserError(
                    _(
                        f"""Vehicle {self.vehicle_id.name} insurance """
                        f"""will expire in {days_to_expire} days, """
                        f"""which is less than or equal to the security """
                        f"""threshold of {vehicle_security_days} days."""
                    )
                )

        # Check the drivers license
        driver_security_days = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("tms.default_driver_license_security_days")
        )
        if driver_security_days and self.driver_id.driver_license_expiration_date:
            expiration_date = self.driver_id.driver_license_expiration_date
            days_to_expire = (expiration_date - datetime.today().date()).days

            if days_to_expire <= vehicle_security_days:
                raise UserError(
                    _(
                        f"""Driver {self.driver_id.name} license will expire """
                        f"""in {days_to_expire} days, which is less than or equal """
                        f"""to the security threshold of {driver_security_days} days."""
                    )
                )

        self.date_start = datetime.now()
        self.start_trip = True

    def button_end_order(self):
        self.date_end = fields.Datetime.now()
        duration = self.date_end - self.date_start
        self.duration = duration.total_seconds() / 3600
        self.diff_duration = round(self.scheduled_duration - self.duration, 2)
        self.start_trip = False
        self.end_trip = True

    def button_refresh_duration(self):
        self.date_end = fields.Datetime.now()
        duration = self.date_end - self.date_start
        self.duration = duration.total_seconds() / 3600

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code("tms.order")

        return super().create(vals_list)

    @api.onchange("vehicle_id")
    def _onchange_vehicle_id_set_driver(self):
        for record in self:
            vehicle = record.vehicle_id
            if vehicle and vehicle.driver_id:
                record.driver_id = vehicle.driver_id
            else:
                record.driver_id = False
