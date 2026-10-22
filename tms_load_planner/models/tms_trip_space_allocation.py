# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class TmsTripSpaceAllocation(models.Model):
    """One space of the trip vehicle, for this trip.

    Cargo points here. A row with cargo is booked. A row without cargo
    is available. A blocked vehicle space is blocked on an open trip.
    A done trip keeps its rows and no longer occupies them.
    """

    _name = "tms.trip.space.allocation"
    _description = "Trip space allocation"
    _order = "vehicle_space_id, id"

    trip_id = fields.Many2one(
        "tms.order",
        string="Trip",
        required=True,
        ondelete="cascade",
        index=True,
    )
    vehicle_space_id = fields.Many2one(
        "tms.vehicle.space",
        string="Vehicle space",
        required=True,
        ondelete="restrict",
        index=True,
    )
    cargo_ids = fields.One2many(
        "tms.cargo",
        "space_allocation_id",
        string="Cargo lines",
    )
    cargo_id = fields.Many2one(
        "tms.cargo",
        string="Cargo",
        compute="_compute_booking",
        store=True,
    )
    state = fields.Selection(
        [
            ("available", "Available"),
            ("booked", "Booked"),
            ("blocked", "Blocked"),
        ],
        compute="_compute_booking",
        store=True,
        index=True,
    )
    zone = fields.Selection(related="vehicle_space_id.zone")
    space_code = fields.Char(related="vehicle_space_id.code")

    _trip_space_uniq = models.Constraint(
        "unique (trip_id, vehicle_space_id)",
        "This trip already has a row for that space.",
    )

    @api.depends("vehicle_space_id.code")
    def _compute_display_name(self):
        for row in self:
            row.display_name = row.vehicle_space_id.code or ""

    @api.depends(
        "cargo_ids",
        "cargo_ids.state",
        "vehicle_space_id.state",
        "trip_id.end_trip",
        "trip_id.stage_id.is_completed",
        "trip_id.stage_id.fold",
    )
    def _compute_booking(self):
        """Booked when cargo is set. Available when it is empty.

        An open trip follows a blocked vehicle space even with no cargo.
        """
        for row in self:
            active = row.cargo_ids.filtered(
                lambda cargo: cargo.state not in ("hold", "unassigned")
            )
            row.cargo_id = active[:1]
            occupies = row.trip_id._occupies_vehicle_space() if row.trip_id else False
            if occupies and row.vehicle_space_id.state == "blocked":
                row.state = "blocked"
            elif active:
                row.state = "booked"
            else:
                row.state = "available"

    @api.constrains("trip_id", "vehicle_space_id")
    def _check_trip_vehicle(self):
        for row in self:
            trip_vehicle = row.trip_id.vehicle_id
            space_vehicle = row.vehicle_space_id.vehicle_id
            if trip_vehicle and space_vehicle and trip_vehicle != space_vehicle:
                raise ValidationError(
                    self.env._(
                        "Space %(code)s is on %(space_vehicle)s. "
                        "%(trip)s uses %(trip_vehicle)s.",
                        code=row.vehicle_space_id.code,
                        space_vehicle=space_vehicle.display_name,
                        trip=row.trip_id.display_name,
                        trip_vehicle=trip_vehicle.display_name,
                    )
                )
