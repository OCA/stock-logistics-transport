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
    route_id = fields.Many2one(
        "tms.route", compute="_compute_route_id", store=True, readonly=False
    )
    route_origin = fields.Char(related="route_id.origin_location_id.display_name")
    route_destination = fields.Char(
        related="route_id.destination_location_id.display_name"
    )

    origin_id = fields.Many2one(
        "res.partner",
        domain="[('tms_location', '=', 'True')]",
        context={"default_tms_location": True},
        compute="_compute_route_id",
        store=True,
        readonly=False,
    )
    destination_id = fields.Many2one(
        "res.partner",
        domain="[('tms_location', '=', 'True')]",
        context={"default_tms_location": True},
        compute="_compute_route_id",
        store=True,
        readonly=False,
    )

    origin_location = fields.Char(string="Origin")
    destination_location = fields.Char(string="Destination")

    driver_id = fields.Many2one(
        "tms.driver",
        string="Driver",
        compute="_compute_vehicle_id_set_driver",
        store=True,
        readonly=False,
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
        compute="_compute_scheduled_duration",
        store=True,
        readonly=False,
    )
    scheduled_date_end = fields.Datetime(
        string="Scheduled End",
        compute="_compute_scheduled_date_end",
        store=True,
        readonly=False,
    )

    start_trip = fields.Boolean(readonly=True)
    end_trip = fields.Boolean(readonly=True)
    date_start = fields.Datetime()
    date_end = fields.Datetime(compute="_compute_date_end", store=True, readonly=False)
    duration = fields.Float(
        string="Trip Duration", compute="_compute_duration", store=True, readonly=False
    )

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

    @api.depends("route")
    def _compute_route_id(self):
        for order in self:
            if order.route:
                order.update({"origin_id": False, "destination_id": False})
            else:
                order.update(
                    {
                        "route_id": False,
                    }
                )

    @api.depends("scheduled_duration", "scheduled_date_start")
    def _compute_scheduled_date_end(self):
        for record in self:
            if record.scheduled_date_start:
                record.scheduled_date_end = record.scheduled_date_start + timedelta(
                    hours=record.scheduled_duration
                )

    @api.depends("scheduled_date_end", "route_id")
    def _compute_scheduled_duration(self):
        for record in self:
            if (
                record.scheduled_date_end and record.scheduled_date_start
            ) and not record.route_id:
                difference = record.scheduled_date_end - record.scheduled_date_start
                record.scheduled_duration = difference.total_seconds() / 3600
            elif record.route_id:
                if (
                    record.route_id.estimated_time_uom.id
                    == self.env.ref("uom.product_uom_day").id
                ):
                    record.scheduled_duration = record.route_id.estimated_time * 24
                else:
                    record.scheduled_duration = record.route_id.estimated_time
            else:
                record.scheduled_duration = 0.0

    @api.depends("duration", "date_start")
    def _compute_date_end(self):
        for record in self:
            if record.date_start:
                record.date_end = record.date_start + timedelta(hours=record.duration)

    @api.depends("date_end")
    def _compute_duration(self):
        for record in self:
            if record.date_end and record.date_start:
                difference = record.date_end - record.date_start
                record.duration = difference.total_seconds() / 3600

    @api.depends("tms_team_id.driver_ids", "crew_id.driver_ids")
    def _compute_driver_ids_domain(self):
        all_drivers = self.env["tms.driver"].search([])
        all_driver_ids = all_drivers.ids
        for order in self:
            order.driver_ids_domain = [(6, 0, all_driver_ids)]
            if order.tms_team_id:
                order.driver_ids_domain = [(6, 0, order.tms_team_id.driver_ids.ids)]
            if order.crew_id:
                order.driver_ids_domain = [(6, 0, order.crew_id.driver_ids.ids)]

    driver_ids_domain = fields.Many2many(
        "tms.driver",
        "team_drivers_rel",
        compute="_compute_driver_ids_domain",
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

    crew_active = fields.Boolean(
        compute="_compute_active_crew", groups="tms.group_tms_crew"
    )

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

    @api.depends("vehicle_id")
    def _compute_vehicle_id_set_driver(self):
        for record in self:
            vehicle = record.vehicle_id
            if vehicle and vehicle.tms_driver_id:
                record.driver_id = vehicle.tms_driver_id
            else:
                record.driver_id = False
