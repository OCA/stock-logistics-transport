# Copyright (C) 2024 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import math
from datetime import datetime, timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare


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
        default=lambda self: self.env._("New"),
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
    route_origin = fields.Many2one(
        "res.partner",
        related="route_id.origin_location_id",
        string="Route origin",
    )
    route_destination = fields.Many2one(
        "res.partner",
        related="route_id.destination_location_id",
        string="Route destination",
    )

    origin_id = fields.Many2one(
        "res.partner",
        string="Origin",
        domain="[('tms_location', '=', True)]",
        context={"default_tms_location": True},
        compute="_compute_route_id",
        store=True,
        readonly=False,
    )
    destination_id = fields.Many2one(
        "res.partner",
        string="Destination",
        domain="[('tms_location', '=', True)]",
        context={"default_tms_location": True},
        compute="_compute_route_id",
        store=True,
        readonly=False,
    )

    origin_location = fields.Many2one(
        "res.partner",
        string="Origin location",
        domain="[('tms_location', '=', True)]",
        context={"default_tms_location": True},
    )
    destination_location = fields.Many2one(
        "res.partner",
        string="Destination location",
        domain="[('tms_location', '=', True)]",
        context={"default_tms_location": True},
    )
    distance = fields.Float(
        compute="_compute_distance",
        store=True,
        readonly=False,
    )
    distance_uom_id = fields.Many2one(
        "uom.uom",
        string="Distance unit",
        compute="_compute_distance",
        store=True,
        readonly=False,
    )
    distance_editable = fields.Boolean(compute="_compute_distance_editable")

    driver_id = fields.Many2one(
        "tms.driver",
        string="Driver",
        compute="_compute_vehicle_id_set_driver",
        store=True,
        readonly=False,
    )
    transport_type = fields.Selection(
        [("cargo", "Cargo"), ("passenger", "Passenger")],
        string="Transport Type",
    )
    vehicle_id = fields.Many2one("fleet.vehicle", string="Vehicle")
    vehicle_operation = fields.Selection(
        related="vehicle_id.operation",
        string="Vehicle Transport Type",
    )
    compartment_ids = fields.One2many("tms.compartment", "order_id")
    equipment_ids = fields.One2many("tms.order.equipment", "order_id")
    odometer_start_id = fields.Many2one(
        "fleet.vehicle.odometer",
        string="Departure reading",
        copy=False,
        index=True,
    )
    odometer_end_id = fields.Many2one(
        "fleet.vehicle.odometer",
        string="Arrival reading",
        copy=False,
        index=True,
    )
    odometer_start = fields.Float(
        string="Odometer at departure",
        compute="_compute_odometer_start",
        inverse="_inverse_odometer_start",
        help="Stored on the vehicle odometer log.",
    )
    odometer_end = fields.Float(
        string="Odometer at arrival",
        compute="_compute_odometer_end",
        inverse="_inverse_odometer_end",
        help="Stored on the vehicle odometer log.",
    )
    distance_loaded = fields.Float(string="Loaded kilometers")
    distance_empty = fields.Float(string="Empty kilometers")
    pod_note = fields.Text(string="Proof of delivery")
    pod_attachment_ids = fields.Many2many(
        "ir.attachment",
        "tms_order_pod_attachment_rel",
        "order_id",
        "attachment_id",
        string="Delivery documents",
    )
    cargo_ids = fields.One2many("tms.cargo", "order_id", copy=False)
    cargo_weight_uom_id = fields.Many2one(
        "uom.uom",
        string="Weight unit",
        compute="_compute_cargo_capacity",
    )
    cargo_volume_uom_id = fields.Many2one(
        "uom.uom",
        string="Volume unit",
        compute="_compute_cargo_capacity",
    )
    cargo_weight = fields.Float(
        string="Total weight",
        compute="_compute_cargo_capacity",
    )
    cargo_volume = fields.Float(
        string="Total volume",
        compute="_compute_cargo_capacity",
    )
    weight_capacity_set = fields.Boolean(compute="_compute_cargo_capacity")
    volume_capacity_set = fields.Boolean(compute="_compute_cargo_capacity")
    capacity_weight = fields.Float(
        string="Available weight",
        compute="_compute_cargo_capacity",
    )
    capacity_volume = fields.Float(
        string="Available volume",
        compute="_compute_cargo_capacity",
    )
    remaining_weight = fields.Float(
        string="Weight remaining",
        compute="_compute_cargo_capacity",
    )
    remaining_volume = fields.Float(
        string="Volume remaining",
        compute="_compute_cargo_capacity",
    )
    cargo_loading_uom_id = fields.Many2one(
        "uom.uom",
        string="Loading meter unit",
        compute="_compute_cargo_capacity",
    )
    cargo_loading_meters = fields.Float(
        string="Loading meters",
        compute="_compute_cargo_capacity",
    )
    cargo_pieces = fields.Float(
        string="Allocated pieces",
        compute="_compute_cargo_capacity",
    )
    loading_uses_length = fields.Boolean(compute="_compute_cargo_capacity")
    loading_capacity_set = fields.Boolean(compute="_compute_cargo_capacity")
    capacity_loading_meters = fields.Float(
        string="Loading meter capacity",
        compute="_compute_cargo_capacity",
    )
    remaining_loading_meters = fields.Float(
        string="Available loading meters",
        compute="_compute_cargo_capacity",
    )
    tms_team_id = fields.Many2one("tms.team", string="Team")
    crew_id = fields.Many2one("tms.crew", string="Crew")

    stage_id = fields.Many2one(
        "tms.stage",
        string="Stage",
        index=True,
        copy=False,
        tracking=True,
        domain="[('stage_type', '=', 'order')]",
        default=lambda self: self._default_stage_id(),
        group_expand="_read_group_stage_ids",
        ondelete="set null",
    )
    allowed_stage_ids = fields.Many2many(
        "tms.stage",
        compute="_compute_allowed_stage_ids",
    )

    scheduled_date_start = fields.Datetime(
        string="Scheduled Start", default=datetime.now()
    )
    scheduled_duration = fields.Float(
        help="Scheduled duration of the work in hours",
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
        domain=lambda self: self.env["res.config.settings"]._time_domain(),
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
        raise ValidationError(self.env._("You must create an TMS order stage first."))

    @api.depends_context("uid")
    def _compute_distance_editable(self):
        editable = not self.env["tms.route"]._routing_provider_ready()
        for order in self:
            order.distance_editable = editable

    @api.depends(
        "route",
        "route_id.distance",
        "route_id.distance_uom",
        "route_id.origin_location_id",
        "route_id.destination_location_id",
        "origin_id",
        "destination_id",
        "origin_id.partner_latitude",
        "origin_id.partner_longitude",
        "destination_id.partner_latitude",
        "destination_id.partner_longitude",
    )
    def _compute_distance(self):
        ready = self.env["tms.route"]._routing_provider_ready()
        for order in self:
            if ready:
                distance, uom = order._trip_distance()
                order.distance = distance
                order.distance_uom_id = uom
                continue
            if (
                not order.distance
                and order.route
                and order.route_id
                and order.route_id.distance
            ):
                uom = order._trip_distance_uom()
                source = order.route_id.distance_uom or uom
                order.distance = order._quantity_in(
                    order.route_id.distance, source, uom
                )
                order.distance_uom_id = uom
                continue
            order.distance = order.distance
            order.distance_uom_id = order.distance_uom_id or order._trip_distance_uom()

    def _trip_distance_uom(self):
        return self.env["res.config.settings"]._configured_uom(
            "tms.default_distance_uom", "uom.product_uom_km"
        )

    def _trip_endpoints(self):
        self.ensure_one()
        if self.route and self.route_id:
            return (
                self.route_id.origin_location_id,
                self.route_id.destination_location_id,
            )
        return self.origin_id, self.destination_id

    def _quantity_in(self, amount, source, target):
        if source and target and source != target:
            return source._compute_quantity(amount, target)
        return amount

    def _trip_distance(self):
        """Distance of the selected route, or between the two locations."""
        self.ensure_one()
        uom = self._trip_distance_uom()
        if self.route and self.route_id and self.route_id.distance:
            source = self.route_id.distance_uom or uom
            return self._quantity_in(self.route_id.distance, source, uom), uom
        origin, destination = self._trip_endpoints()
        return self._distance_between_locations(origin, destination, uom)

    def _partner_has_coordinates(self, partner):
        return bool(
            partner and (partner.partner_latitude or partner.partner_longitude)
        )

    def _distance_between_locations(self, origin, destination, uom):
        """Great-circle distance. A routing module can replace this."""
        self.ensure_one()
        if not self._partner_has_coordinates(
            origin
        ) or not self._partner_has_coordinates(destination):
            return 0.0, uom
        kilometer = self.env.ref("uom.product_uom_km", raise_if_not_found=False)
        kilometers = self._great_circle_kilometers(origin, destination)
        if kilometer and uom:
            return kilometer._compute_quantity(kilometers, uom), uom
        return kilometers, uom or kilometer

    def _great_circle_kilometers(self, origin, destination):
        earth_radius = 6371.0
        latitude_1 = math.radians(origin.partner_latitude)
        latitude_2 = math.radians(destination.partner_latitude)
        delta_lat = latitude_2 - latitude_1
        delta_lon = math.radians(
            destination.partner_longitude - origin.partner_longitude
        )
        chord = math.sin(delta_lat / 2.0) ** 2 + math.cos(latitude_1) * math.cos(
            latitude_2
        ) * math.sin(delta_lon / 2.0) ** 2
        return 2.0 * earth_radius * math.asin(math.sqrt(chord))

    @api.onchange("origin_id", "destination_id", "route", "route_id")
    def _onchange_distance(self):
        if self.env["tms.route"]._routing_provider_ready() or self.distance:
            return
        if not (self.route and self.route_id and self.route_id.distance):
            return
        uom = self._trip_distance_uom()
        source = self.route_id.distance_uom or uom
        self.distance = self._quantity_in(self.route_id.distance, source, uom)
        self.distance_uom_id = uom

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
        drivers = self.env["tms.driver"]
        all_driver_ids = drivers.browse(drivers._search([])).ids
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

    @api.depends("tms_team_id", "tms_team_id.vehicle_ids", "transport_type")
    def _compute_vehicle_ids_domain(self):
        vehicles = self.env["fleet.vehicle"]
        for order in self:
            domain = []
            if order.tms_team_id:
                domain.append(("tms_team_id", "=", order.tms_team_id.id))
            if order.transport_type:
                domain.append(("operation", "=", order.transport_type))
            order.vehicle_ids_domain = vehicles.search(domain)

    vehicle_ids_domain = fields.Many2many(
        "fleet.vehicle",
        "team_vehicles_rel",
        compute="_compute_vehicle_ids_domain",
        default=lambda self: self.env["fleet.vehicle"]
        .browse(self.env["fleet.vehicle"]._search([]))
        .ids,
    )

    @api.depends("tms_team_id")
    def _compute_crew_ids_domain(self):
        crews = self.env["tms.crew"]
        all_crews_ids = crews.browse(crews._search([])).ids
        for order in self:
            if order.tms_team_id:
                order.crew_ids_domain = [(6, 0, order.tms_team_id.crew_ids.ids)]
            else:
                order.crew_ids_domain = [(6, 0, all_crews_ids)]

    crew_ids_domain = fields.Many2many(
        "tms.crew",
        "team_crews_rel",
        compute="_compute_crew_ids_domain",
        default=lambda self: self.env["tms.crew"]
        .browse(self.env["tms.crew"]._search([]))
        .ids,
    )

    @api.depends("crew_id")
    def _compute_active_crew(self):
        for order in self:
            order.crew_active = bool(order.crew_id)
            if order.crew_id:
                vehicle = order.crew_id.default_vehicle_id
                if (
                    order.transport_type
                    and vehicle.operation
                    and vehicle.operation != order.transport_type
                ):
                    order.vehicle_id = False
                else:
                    order.vehicle_id = vehicle.id
            else:
                order.vehicle_id = order.vehicle_id

    crew_active = fields.Boolean(
        compute="_compute_active_crew", groups="tms.group_tms_crew"
    )

    # Constraints
    _name_uniq = models.Constraint("unique (name)", "Trip name already exists!")
    _duration_ge_zero = models.Constraint(
        "CHECK (scheduled_duration >= 0)",
        "Scheduled duration must be greater than or equal to zero!",
    )

    @api.depends("odometer_start_id.value")
    def _compute_odometer_start(self):
        for order in self:
            order.odometer_start = order.odometer_start_id.value

    @api.depends("odometer_end_id.value")
    def _compute_odometer_end(self):
        for order in self:
            order.odometer_end = order.odometer_end_id.value

    def _inverse_odometer_start(self):
        for order in self:
            order._assign_odometer_reading(
                "odometer_start_id", order.odometer_start, order.date_start
            )

    def _inverse_odometer_end(self):
        for order in self:
            order._assign_odometer_reading(
                "odometer_end_id", order.odometer_end, order.date_end
            )

    def _odometer_reading_date(self, moment):
        self.ensure_one()
        if not moment:
            return fields.Datetime.now()
        return fields.Datetime.to_datetime(moment)

    def _assign_odometer_reading(self, reading_field, value, moment):
        """Create or update the Fleet odometer line behind a trip reading."""
        self.ensure_one()
        if not self.vehicle_id:
            raise UserError(
                self.env._("Set the vehicle before recording an odometer reading.")
            )
        reading = self[reading_field]
        vals = {
            "value": value,
            "date": self._odometer_reading_date(moment),
            "vehicle_id": self.vehicle_id.id,
        }
        if reading and reading.vehicle_id == self.vehicle_id:
            reading.write(vals)
            return
        self[reading_field] = self.env["fleet.vehicle.odometer"].create(vals)

    def _sync_odometer_readings(self):
        for order in self:
            if not order.vehicle_id:
                order.write({"odometer_start_id": False, "odometer_end_id": False})
                continue
            if order.odometer_start_id or order.odometer_start:
                order._assign_odometer_reading(
                    "odometer_start_id", order.odometer_start, order.date_start
                )
            if order.odometer_end_id or order.odometer_end:
                order._assign_odometer_reading(
                    "odometer_end_id", order.odometer_end, order.date_end
                )

    @api.constrains(
        "odometer_start_id",
        "odometer_end_id",
        "distance_loaded",
        "distance_empty",
    )
    def _check_odometer_distances(self):
        for order in self:
            if (
                order.odometer_end
                and order.odometer_start
                and order.odometer_end < order.odometer_start
            ):
                raise ValidationError(
                    self.env._(
                        "The arrival odometer must be greater than the departure "
                        "odometer."
                    )
                )
            driven = order.odometer_end - order.odometer_start
            split = order.distance_loaded + order.distance_empty
            if order.odometer_end and order.odometer_start and split:
                if abs(split - driven) > 0.01:
                    raise ValidationError(
                        self.env._(
                            "Loaded and empty kilometers must add up to the "
                            "odometer difference."
                        )
                    )

    @api.model
    def _read_group_stage_ids(self, stages, domain, order=None):
        order = order or "sequence, id"
        team_id = False
        for leaf in domain or []:
            if (
                isinstance(leaf, (list, tuple))
                and len(leaf) == 3
                and leaf[0] == "tms_team_id"
                and leaf[1] == "="
            ):
                team_id = leaf[2]
                break
        if team_id:
            team = self.env["tms.team"].browse(team_id).exists()
            team_stages = team.stage_ids.filtered(
                lambda stage: stage.stage_type == "order"
            )
            if team_stages:
                return team_stages.sorted(lambda stage: (stage.sequence, stage.id))
        return self.env["tms.stage"].search([("stage_type", "=", "order")], order=order)

    @api.depends(
        "tms_team_id.stage_ids",
        "tms_team_id.operation",
        "transport_type",
        "vehicle_id.operation",
    )
    def _compute_allowed_stage_ids(self):
        for order in self:
            if order.tms_team_id:
                order.allowed_stage_ids = order.tms_team_id.stage_ids.filtered(
                    lambda stage: stage.stage_type == "order"
                )
            else:
                order.allowed_stage_ids = self.env["tms.stage"]._stages_for_operation(
                    order.transport_type or order.vehicle_id.operation
                )

    def _trip_operation(self):
        self.ensure_one()
        if self.transport_type:
            return self.transport_type
        if self.tms_team_id.operation:
            return self.tms_team_id.operation
        return self.vehicle_id.operation or False

    @api.onchange("transport_type")
    def _onchange_transport_type(self):
        if (
            self.vehicle_id
            and self.transport_type
            and self.vehicle_id.operation
            and self.vehicle_id.operation != self.transport_type
        ):
            self.vehicle_id = False

    @api.onchange("vehicle_id")
    def _onchange_vehicle_id_transport_type(self):
        if (
            not self.transport_type
            and self.vehicle_id.operation in ("cargo", "passenger")
        ):
            self.transport_type = self.vehicle_id.operation

    @api.constrains("transport_type", "vehicle_id")
    def _check_vehicle_transport_type(self):
        for order in self:
            vehicle = order.vehicle_id
            if (
                order.transport_type
                and vehicle
                and vehicle.operation
                and vehicle.operation != order.transport_type
            ):
                raise ValidationError(
                    self.env._(
                        "The vehicle must use the same transport type as the trip."
                    )
                )

    def _check_stage_before_start(self):
        loaded = self.env.ref("tms.tms_stage_order_loaded", raise_if_not_found=False)
        for order in self:
            if order._trip_operation() != "cargo" or not loaded:
                continue
            if order.stage_id == loaded:
                continue
            shippable = order.cargo_ids.filtered(lambda cargo: cargo.state != "hold")
            held = order.cargo_ids.filtered(lambda cargo: cargo.state == "hold")
            if shippable or not held:
                raise UserError(self.env._("Load the cargo before starting this trip."))

    def _set_in_transit_stage(self):
        in_transit = self.env.ref(
            "tms.tms_stage_order_in_transit", raise_if_not_found=False
        )
        if in_transit:
            self.stage_id = in_transit

    def _resource_is_free(self):
        """A done or cancelled trip no longer holds its vehicle and driver."""
        self.ensure_one()
        if self.end_trip:
            return True
        stage = self.stage_id
        return bool(stage) and (stage.is_completed or stage.fold)

    def _resource_window(self):
        """The time this trip needs the vehicle and the driver.

        A trip that has started and not ended stays busy until it is done.
        """
        self.ensure_one()
        if self.start_trip and not self.end_trip:
            return self.date_start or self.scheduled_date_start, False
        return (
            self.date_start or self.scheduled_date_start,
            self.date_end or self.scheduled_date_end,
        )

    def _windows_overlap(self, other):
        start, end = self._resource_window()
        other_start, other_end = other._resource_window()
        if start and other_end and start >= other_end:
            return False
        if other_start and end and other_start >= end:
            return False
        return True

    def _check_resource_overlap(self, field_name):
        self.ensure_one()
        resource = self[field_name]
        if not resource or self._resource_is_free():
            return
        others = self.search(
            [
                ("id", "!=", self.id),
                (field_name, "=", resource.id),
                ("end_trip", "=", False),
                ("stage_id.is_completed", "=", False),
                ("stage_id.fold", "=", False),
            ]
        )
        for other in others:
            if not self._windows_overlap(other):
                continue
            end = other.date_end or other.scheduled_date_end
            if other.start_trip or not end:
                raise ValidationError(
                    self.env._(
                        "%(resource)s is already on %(trip)s until that trip is done.",
                        resource=resource.display_name,
                        trip=other.display_name,
                    )
                )
            raise ValidationError(
                self.env._(
                    "%(resource)s is already on %(trip)s until %(until)s.",
                    resource=resource.display_name,
                    trip=other.display_name,
                    until=fields.Datetime.to_string(end),
                )
            )

    def _check_vehicle_and_driver_free(self):
        for order in self:
            order._check_resource_overlap("vehicle_id")
            order._check_resource_overlap("driver_id")

    def _check_driver_not_on_trip(self):
        for order in self:
            if not order.driver_id:
                continue
            other = self.search(
                [
                    ("id", "!=", order.id),
                    ("driver_id", "=", order.driver_id.id),
                    ("start_trip", "=", True),
                    ("end_trip", "=", False),
                ],
                limit=1,
            )
            if other:
                raise UserError(
                    self.env._(
                        "Driver %(driver)s is already on trip %(trip)s.",
                        driver=order.driver_id.name,
                        trip=other.name,
                    )
                )

    def _set_driver_trip_stage(self, on_trip):
        in_trip = self.env.ref("tms.tms_stage_driver_in_trip", raise_if_not_found=False)
        in_base = self.env.ref("tms.tms_stage_driver_in_base", raise_if_not_found=False)
        target = in_trip if on_trip else in_base
        if not target:
            return
        for order in self:
            driver = order.driver_id
            if not driver:
                continue
            if not on_trip:
                still_out = self.search(
                    [
                        ("id", "!=", order.id),
                        ("driver_id", "=", driver.id),
                        ("start_trip", "=", True),
                        ("end_trip", "=", False),
                    ],
                    limit=1,
                )
                if still_out:
                    continue
            driver.sudo().stage_id = target

    def _set_arrived_stage(self):
        arrived = self.env.ref("tms.tms_stage_order_arrived", raise_if_not_found=False)
        if arrived:
            self.stage_id = arrived

    def _sync_loaded_stage(self):
        loaded = self.env.ref("tms.tms_stage_order_loaded", raise_if_not_found=False)
        confirmed = self.env.ref(
            "tms.tms_stage_order_confirmed", raise_if_not_found=False
        )
        if not loaded or not confirmed:
            return
        for order in self:
            if order._trip_operation() != "cargo":
                continue
            shippable = order.cargo_ids.filtered(lambda cargo: cargo.state != "hold")
            all_loaded = bool(shippable) and all(
                cargo.state == "loaded" for cargo in shippable
            )
            if all_loaded and order.stage_id == confirmed:
                order.stage_id = loaded
            elif not all_loaded and order.stage_id == loaded:
                order.stage_id = confirmed

    @api.depends(
        "cargo_ids.weight",
        "cargo_ids.weight_uom_id",
        "cargo_ids.volume",
        "cargo_ids.volume_uom_id",
        "cargo_ids.state",
        "cargo_ids.quantity",
        "cargo_ids.uom_id",
        "cargo_ids.loading_meters",
        "cargo_ids.is_stackable",
        "vehicle_id.model_id.loading_length",
        "vehicle_id.model_id.loading_length_uom_id",
        "vehicle_id.model_id.pallet_capacity",
        "equipment_ids.vehicle_id.model_id.loading_length",
        "equipment_ids.vehicle_id.model_id.loading_length_uom_id",
        "equipment_ids.vehicle_id.model_id.pallet_capacity",
        "vehicle_id.operation",
        "vehicle_id.model_id.max_volume_capacity",
        "vehicle_id.model_id.max_volume_uom_id",
        "vehicle_id.model_id.max_weight_capacity",
        "vehicle_id.model_id.max_weight_uom_id",
        "equipment_ids.dropped",
        "equipment_ids.role",
        "equipment_ids.vehicle_id.model_id.max_volume_capacity",
        "equipment_ids.vehicle_id.model_id.max_volume_uom_id",
        "equipment_ids.vehicle_id.model_id.max_weight_capacity",
        "equipment_ids.vehicle_id.model_id.max_weight_uom_id",
    )
    def _compute_cargo_capacity(self):
        settings = self.env["res.config.settings"]
        weight_uom = settings._configured_uom(
            "tms.default_weight_uom", "uom.product_uom_kgm"
        )
        volume_uom = settings._configured_uom(
            "tms.default_volume_uom", "uom.product_uom_cubic_meter"
        )
        length_uoms = self._distance_uoms()
        for order in self:
            order.cargo_weight_uom_id = weight_uom
            order.cargo_volume_uom_id = volume_uom
            order.cargo_weight = order._sum_cargo("weight", "weight_uom_id", weight_uom)
            order.cargo_volume = order._sum_cargo("volume", "volume_uom_id", volume_uom)
            limits = order._cargo_capacity_limits(weight_uom, volume_uom)
            order.weight_capacity_set = limits["weight"] is not None
            order.volume_capacity_set = limits["volume"] is not None
            order.capacity_weight = limits["weight"] or 0.0
            order.capacity_volume = limits["volume"] or 0.0
            order.remaining_weight = order.capacity_weight - order.cargo_weight
            order.remaining_volume = order.capacity_volume - order.cargo_volume
            order.cargo_loading_meters = order._sum_loading_meters()
            uses_length, piece_uom, pieces = order._pieces_allocation(length_uoms)
            order.loading_uses_length = uses_length
            order.cargo_pieces = pieces
            order.cargo_loading_uom_id = piece_uom
            if uses_length:
                length_limit = order._loading_capacity_limit(piece_uom)
            else:
                length_limit = order._pallet_capacity_limit()
            order.loading_capacity_set = length_limit is not None
            order.capacity_loading_meters = length_limit or 0.0
            order.remaining_loading_meters = (
                order.capacity_loading_meters - order.cargo_pieces
            )

    def _sum_cargo(self, amount_field, uom_field, target_uom):
        self.ensure_one()
        total = 0.0
        for cargo in self.cargo_ids.filtered(lambda line: line.state != "hold"):
            amount = cargo[amount_field]
            uom = cargo[uom_field]
            if target_uom and uom:
                total += uom._compute_quantity(amount, target_uom)
            else:
                total += amount
        return total

    def _sum_model_measure(self, vehicles, amount_field, uom_field, target_uom):
        total = 0.0
        found = False
        for vehicle in vehicles:
            model = vehicle.model_id
            amount = model[amount_field]
            uom = model[uom_field]
            if not amount or not uom or not target_uom:
                continue
            found = True
            total += uom._compute_quantity(amount, target_uom)
        return total if found else None

    def _coupled_trailers(self):
        self.ensure_one()
        return self.equipment_ids.filtered(
            lambda line: line.role == "trailer" and not line.dropped
        ).vehicle_id

    def _cargo_capacity_limits(self, weight_uom, volume_uom):
        self.ensure_one()
        trailers = self._coupled_trailers()
        power = self.vehicle_id.filtered(lambda vehicle: vehicle.operation == "cargo")
        trailer_volume = self._sum_model_measure(
            trailers, "max_volume_capacity", "max_volume_uom_id", volume_uom
        )
        power_volume = self._sum_model_measure(
            power, "max_volume_capacity", "max_volume_uom_id", volume_uom
        )
        trailer_weight = self._sum_model_measure(
            trailers, "max_weight_capacity", "max_weight_uom_id", weight_uom
        )
        power_weight = self._sum_model_measure(
            power, "max_weight_capacity", "max_weight_uom_id", weight_uom
        )
        if trailer_volume is not None:
            volume_limit = trailer_volume
        else:
            volume_limit = power_volume
        if trailer_weight is not None and power_weight is not None:
            weight_limit = min(trailer_weight, power_weight)
        elif trailer_weight is not None:
            weight_limit = trailer_weight
        else:
            weight_limit = power_weight
        return {"weight": weight_limit, "volume": volume_limit}

    @api.model
    def _distance_uoms(self):
        """Meters, feet, and the other units that share their reference."""
        meter = self.env.ref("uom.product_uom_meter", raise_if_not_found=False)
        if not meter:
            return self.env["uom.uom"]
        root = meter
        seen = set()
        while root.relative_uom_id and root.id not in seen:
            seen.add(root.id)
            root = root.relative_uom_id
        length = self.env["uom.uom"]
        for uom in self.env["uom.uom"].search([]):
            current = uom
            walked = set()
            while current and current.id not in walked:
                if current == root:
                    length |= uom
                    break
                walked.add(current.id)
                current = current.relative_uom_id
        return length

    def _pieces_allocation(self, length_uoms):
        """Pieces in a distance unit use loading length. A unit count uses pallets."""
        self.ensure_one()
        lines = self.cargo_ids.filtered(lambda line: line.state != "hold")
        uoms = lines.uom_id
        if lines and uoms and all(uom in length_uoms for uom in uoms):
            target = lines[:1].uom_id
            total = 0.0
            for line in lines:
                if line.uom_id and line.uom_id != target:
                    total += line.uom_id._compute_quantity(line.quantity, target)
                else:
                    total += line.quantity
            return True, target, total
        return False, self.env["uom.uom"], sum(lines.mapped("quantity"))

    def _sum_loading_meters(self):
        self.ensure_one()
        total = 0.0
        for cargo in self.cargo_ids.filtered(lambda line: line.state != "hold"):
            meters = cargo.loading_meters
            if not cargo.is_stackable:
                meters *= 2.0
            total += meters
        return total

    def _sum_model_length(self, vehicles, length_uom):
        total = 0.0
        found = False
        for vehicle in vehicles:
            amount = vehicle.model_id.loading_length
            uom = vehicle.model_id.loading_length_uom_id
            if not amount or not uom or not length_uom:
                continue
            found = True
            total += uom._compute_quantity(amount, length_uom)
        return total if found else None

    def _sum_model_pallets(self, vehicles):
        total = 0
        found = False
        for vehicle in vehicles:
            amount = vehicle.model_id.pallet_capacity
            if not amount:
                continue
            found = True
            total += amount
        return float(total) if found else None

    def _pallet_capacity_limit(self):
        self.ensure_one()
        trailers = self._coupled_trailers()
        trailer_pallets = self._sum_model_pallets(trailers)
        if trailer_pallets is not None:
            return trailer_pallets
        power = self.vehicle_id.filtered(lambda vehicle: vehicle.operation == "cargo")
        return self._sum_model_pallets(power)

    def _loading_capacity_limit(self, length_uom):
        self.ensure_one()
        trailers = self._coupled_trailers()
        trailer_length = self._sum_model_length(trailers, length_uom)
        if trailer_length is not None:
            return trailer_length
        power = self.vehicle_id.filtered(lambda vehicle: vehicle.operation == "cargo")
        return self._sum_model_length(power, length_uom)

    def _measure_exceeds(self, total, limit, uom):
        if limit is None or not uom:
            return False
        rounding = uom.rounding or 0.01
        return float_compare(total, limit, precision_rounding=rounding) > 0

    @api.constrains("vehicle_id", "cargo_ids")
    def _check_cargo_vehicle(self):
        for order in self:
            vehicle = order.vehicle_id
            if order.cargo_ids and vehicle and vehicle.operation != "cargo":
                raise ValidationError(
                    self.env._(
                        "Cargo can be added only when the vehicle manages cargo."
                    )
                )

    def _check_cargo_before_start(self):
        for order in self:
            vehicle = order.vehicle_id
            if not vehicle or vehicle.operation != "cargo":
                continue
            held = order.cargo_ids.filtered(lambda cargo: cargo.state == "hold")
            if not order.cargo_ids:
                raise UserError(self.env._("Add the cargo before starting this trip."))
            if held and len(held) == len(order.cargo_ids):
                continue
            weight_uom = order.cargo_weight_uom_id
            volume_uom = order.cargo_volume_uom_id
            if order._measure_exceeds(
                order.cargo_volume,
                order.capacity_volume if order.volume_capacity_set else None,
                volume_uom,
            ):
                raise UserError(
                    self.env._(
                        "Cargo volume %(volume)s %(uom)s exceeds the available "
                        "capacity of %(capacity)s %(uom)s.",
                        volume=order.cargo_volume,
                        capacity=order.capacity_volume,
                        uom=volume_uom.name,
                    )
                )
            if order._measure_exceeds(
                order.cargo_weight,
                order.capacity_weight if order.weight_capacity_set else None,
                weight_uom,
            ):
                raise UserError(
                    self.env._(
                        "Cargo weight %(weight)s %(uom)s exceeds the available "
                        "capacity of %(capacity)s %(uom)s.",
                        weight=order.cargo_weight,
                        capacity=order.capacity_weight,
                        uom=weight_uom.name,
                    )
                )

    def button_start_order(self):
        self._check_cargo_before_start()
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
                    self.env._(
                        "Vehicle %(vehicle)s insurance will expire in "
                        "%(days)s days, which is less than or equal to the "
                        "security threshold of %(threshold)s days.",
                        vehicle=self.vehicle_id.name,
                        days=days_to_expire,
                        threshold=vehicle_security_days,
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

            if days_to_expire <= driver_security_days:
                raise UserError(
                    self.env._(
                        "Driver %(driver)s license will expire in %(days)s days, "
                        "which is less than or equal to the security threshold "
                        "of %(threshold)s days.",
                        driver=self.driver_id.name,
                        days=days_to_expire,
                        threshold=driver_security_days,
                    )
                )

        self._check_stage_before_start()
        self._check_driver_not_on_trip()
        self.date_start = datetime.now()
        self.start_trip = True
        self._set_in_transit_stage()
        self._set_driver_trip_stage(on_trip=True)

    def action_split_trip(self):
        """Open an empty trip with the same route so cargo can be moved onto it."""
        self.ensure_one()
        if self.start_trip or self.end_trip:
            raise UserError(self.env._("This trip has already started."))
        name = self.env["ir.sequence"].next_by_code("tms.order") or self.env._("New")
        new_trip = self.copy(
            default={
                "name": name,
                "start_trip": False,
                "end_trip": False,
                "date_start": False,
                "date_end": False,
            }
        )
        if self.stage_id:
            new_trip.stage_id = self.stage_id
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Trip"),
            "res_model": "tms.order",
            "view_mode": "form",
            "res_id": new_trip.id,
            "target": "current",
        }

    def button_end_order(self):
        self.date_end = fields.Datetime.now()
        duration = self.date_end - self.date_start
        self.duration = duration.total_seconds() / 3600
        self.diff_duration = round(self.scheduled_duration - self.duration, 2)
        self.start_trip = False
        self.end_trip = True
        self._set_arrived_stage()
        self._set_driver_trip_stage(on_trip=False)

    def button_refresh_duration(self):
        self.date_end = fields.Datetime.now()
        duration = self.date_end - self.date_start
        self.duration = duration.total_seconds() / 3600

    def write(self, vals):
        transport_type = vals.get("transport_type")
        if (
            transport_type
            and "vehicle_id" not in vals
            and not self.env.context.get("skip_transport_type_vehicle_clear")
        ):
            mismatched = self.filtered(
                lambda order: order.vehicle_id.operation
                and order.vehicle_id.operation != transport_type
            )
            if mismatched:
                mismatched.with_context(skip_transport_type_vehicle_clear=True).write(
                    {"vehicle_id": False}
                )
        result = super().write(vals)
        if not self.env.context.get("skip_loaded_stage_sync") and {
            "stage_id",
            "vehicle_id",
            "tms_team_id",
        } & set(vals):
            self.with_context(skip_loaded_stage_sync=True)._sync_loaded_stage()
        if not self.env.context.get("skip_odometer_sync") and {
            "date_start",
            "date_end",
            "vehicle_id",
            "odometer_start",
            "odometer_end",
        } & set(vals):
            self.with_context(skip_odometer_sync=True)._sync_odometer_readings()
        watched = {
            "vehicle_id",
            "driver_id",
            "scheduled_date_start",
            "scheduled_date_end",
            "scheduled_duration",
            "date_start",
            "date_end",
            "duration",
            "stage_id",
            "start_trip",
            "end_trip",
        }
        if watched & set(vals) and not self.env.context.get("skip_resource_overlap"):
            self.with_context(
                skip_resource_overlap=True
            )._check_vehicle_and_driver_free()
        return result

    def _default_transport_type(self, vals):
        if vals.get("transport_type") in ("cargo", "passenger"):
            return vals["transport_type"]
        team = self.env["tms.team"].browse(vals.get("tms_team_id")).exists()
        if team.operation in ("cargo", "passenger"):
            return team.operation
        vehicle = self.env["fleet.vehicle"].browse(vals.get("vehicle_id")).exists()
        if vehicle.operation in ("cargo", "passenger"):
            return vehicle.operation
        return False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", self.env._("New")) == self.env._("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code("tms.order")
            transport_type = self._default_transport_type(vals)
            if transport_type:
                vals["transport_type"] = transport_type

        orders = super().create(vals_list)
        orders.with_context(skip_resource_overlap=True)._check_vehicle_and_driver_free()
        return orders

    @api.depends("vehicle_id")
    def _compute_vehicle_id_set_driver(self):
        for record in self:
            vehicle = record.vehicle_id
            if vehicle and vehicle.tms_driver_id:
                record.driver_id = vehicle.tms_driver_id
            else:
                record.driver_id = False
