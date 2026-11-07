# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class TmsCargo(models.Model):
    _inherit = "tms.cargo"

    space_allocation_id = fields.Many2one(
        "tms.trip.space.allocation",
        string="Space",
        ondelete="set null",
        index=True,
        copy=False,
        help="Seat, cabin, or row reserved on this cargo's trip.",
    )
    _space_allocation_uniq = models.Constraint(
        "unique (space_allocation_id)",
        "This space allocation already has cargo.",
    )
    space_trip_date = fields.Datetime(
        related="order_id.scheduled_date_start",
        string="Trip date",
        store=True,
    )
    booking_type = fields.Selection(
        [
            ("shared_space", "Shared space"),
            ("full_asset", "Full asset"),
        ],
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("booking_type") or not vals.get("sale_line_id"):
                continue
            line = self.env["sale.order.line"].browse(vals["sale_line_id"])
            vals["booking_type"] = line.booking_type
        records = super().create(vals_list)
        held = records.filtered(
            lambda cargo: cargo.state in ("hold", "unassigned")
            and cargo.space_allocation_id
        )
        if held:
            held.write({"space_allocation_id": False})
        return records

    def write(self, vals):
        result = super().write(vals)
        release = self.browse()
        if vals.get("state") in ("hold", "unassigned"):
            release = self.filtered("space_allocation_id")
        if "order_id" in vals:
            release |= self.filtered(
                lambda cargo: cargo.space_allocation_id
                and cargo.space_allocation_id.trip_id != cargo.order_id
            )
        if release:
            release.write({"space_allocation_id": False})
        return result

    def _allocated_space(self):
        self.ensure_one()
        return self.space_allocation_id.vehicle_space_id

    @api.constrains(
        "weight",
        "weight_uom_id",
        "volume",
        "volume_uom_id",
        "order_id",
        "state",
    )
    def _check_trip_capacity(self):
        for cargo in self.filtered("order_id"):
            vehicle = cargo.order_id.vehicle_id
            if not vehicle:
                continue
            cargo.order_id._check_vehicle_can_carry_load(vehicle)

    def _other_space_cargo(self):
        self.ensure_one()
        return self.order_id.cargo_ids.filtered(
            lambda line: line.id != self.id
            and line.state not in ("hold", "unassigned")
            and line.space_allocation_id
        )

    @api.constrains("space_allocation_id", "order_id", "is_stackable", "state")
    def _check_space_load(self):
        placed = self.filtered(
            lambda line: line.order_id and line.space_allocation_id
        )
        for cargo in placed:
            cargo._check_space_is_free()
            cargo._check_space_is_supported()
            cargo._check_nothing_stacked_above()

    def _check_space_is_free(self):
        self.ensure_one()
        if self.state == "hold" or not self.order_id:
            return
        if not self.order_id._occupies_vehicle_space():
            return
        space = self._allocated_space()
        taken = self._other_space_cargo().filtered(
            lambda line, space=space: line._allocated_space() == space
        )
        if taken:
            raise ValidationError(
                self.env._(
                    "Space %(code)s already has cargo.",
                    code=space.code,
                )
            )
        self._check_space_is_free_on_vehicle()

    def _check_space_is_free_on_vehicle(self):
        """The space stays taken on this vehicle until the other trip is done."""
        self.ensure_one()
        vehicle = self.order_id.vehicle_id
        if not vehicle:
            return
        space = self._allocated_space()
        others = self.env["tms.cargo"].search(
            [
                ("id", "!=", self.id),
                ("space_allocation_id.vehicle_space_id", "=", space.id),
                ("state", "not in", ("hold", "unassigned")),
                ("order_id", "!=", self.order_id.id),
                ("order_id.vehicle_id", "=", vehicle.id),
            ]
        )
        for other in others:
            trip = other.order_id
            if not trip._occupies_vehicle_space():
                continue
            if not self.order_id._overlaps_occupancy(trip):
                continue
            end = trip.date_end or trip.scheduled_date_end
            if end:
                raise ValidationError(
                    self.env._(
                        "Space %(code)s is in use on %(trip)s until %(until)s.",
                        code=space.code,
                        trip=trip.display_name,
                        until=fields.Datetime.to_string(end),
                    )
                )
            raise ValidationError(
                self.env._(
                    "Space %(code)s is in use on %(trip)s until that trip is done.",
                    code=space.code,
                    trip=trip.display_name,
                )
            )

    def _check_space_is_supported(self):
        self.ensure_one()
        space = self._allocated_space()
        if self.state == "hold" or space.pos_z <= 0.05:
            return
        below = space.supporting_space(space.vehicle_id.space_ids)
        if not below:
            raise ValidationError(
                self.env._(
                    "Space %(code)s has no slot under it.",
                    code=space.code,
                )
            )
        under = self._other_space_cargo().filtered(
            lambda line, below=below: line._allocated_space() == below
        )
        if not under:
            raise ValidationError(
                self.env._(
                    "Load %(below)s before stacking on %(code)s.",
                    below=below.code,
                    code=space.code,
                )
            )
        if any(not line.is_stackable for line in under):
            raise ValidationError(
                self.env._(
                    "The cargo in %(below)s is not stackable, "
                    "so %(code)s cannot be loaded.",
                    below=below.code,
                    code=space.code,
                )
            )

    def _check_nothing_stacked_above(self):
        self.ensure_one()
        if self.is_stackable and self.state != "hold":
            return
        spaces = self._allocated_space().vehicle_id.space_ids
        own = self._allocated_space()
        for other in self._other_space_cargo():
            other_space = other._allocated_space()
            support = other_space.supporting_space(spaces)
            if support == own:
                raise ValidationError(
                    self.env._(
                        "The cargo in %(below)s is not stackable, "
                        "so %(code)s cannot be loaded.",
                        below=own.code,
                        code=other_space.code,
                    )
                )

    @api.constrains("space_allocation_id", "order_id")
    def _check_space_allocation(self):
        for cargo in self.filtered("space_allocation_id"):
            allocation = cargo.space_allocation_id
            space = allocation.vehicle_space_id
            if cargo.order_id and allocation.trip_id != cargo.order_id:
                raise ValidationError(
                    self.env._(
                        "Space %(space)s is reserved on %(allocation_trip)s.",
                        space=space.code,
                        allocation_trip=allocation.trip_id.display_name,
                    )
                )
            trip = cargo.order_id
            if (
                space.state == "blocked"
                and trip
                and trip._occupies_vehicle_space()
            ):
                raise ValidationError(
                    self.env._(
                        "Space %(code)s is blocked.",
                        code=space.code,
                    )
                )
