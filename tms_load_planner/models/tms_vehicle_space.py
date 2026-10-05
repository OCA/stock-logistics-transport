# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class TmsVehicleSpace(models.Model):
    """One slot on a vehicle, copied from the model layout.

    Available means the slot can be booked. Blocked means it is out of
    service on this vehicle.
    """

    _name = "tms.vehicle.space"
    _description = "Vehicle space"
    _order = "pos_x, pos_y, pos_z, code, id"

    vehicle_id = fields.Many2one(
        "fleet.vehicle",
        string="Vehicle",
        required=True,
        ondelete="cascade",
        index=True,
    )
    model_space_id = fields.Many2one(
        "tms.vehicle.model.space",
        string="Model space",
        required=True,
        ondelete="restrict",
        index=True,
    )
    state = fields.Selection(
        [
            ("available", "Available"),
            ("blocked", "Blocked"),
        ],
        default="available",
        required=True,
        index=True,
    )
    cargo_count = fields.Integer(compute="_compute_cargo_count")
    code = fields.Char(related="model_space_id.code", store=True)
    zone = fields.Selection(related="model_space_id.zone", store=True)
    is_premium = fields.Boolean(related="model_space_id.is_premium")
    pos_x = fields.Float(related="model_space_id.pos_x", store=True)
    pos_y = fields.Float(related="model_space_id.pos_y", store=True)
    pos_z = fields.Float(related="model_space_id.pos_z", store=True)
    size_length = fields.Float(related="model_space_id.size_length", store=True)
    size_width = fields.Float(related="model_space_id.size_width", store=True)
    size_height = fields.Float(related="model_space_id.size_height", store=True)

    _vehicle_model_space_uniq = models.Constraint(
        "unique (vehicle_id, model_space_id)",
        "This vehicle already has that space.",
    )

    @api.depends("model_space_id.code")
    def _compute_display_name(self):
        for space in self:
            space.display_name = space.model_space_id.code or ""

    @api.constrains("vehicle_id", "model_space_id")
    def _check_vehicle_model(self):
        for space in self:
            vehicle_model = space.vehicle_id.model_id
            space_model = space.model_space_id.model_id
            if vehicle_model and space_model and vehicle_model != space_model:
                raise ValidationError(
                    self.env._(
                        "Space %(code)s belongs to %(space_model)s. "
                        "%(vehicle)s is a %(vehicle_model)s.",
                        code=space.model_space_id.code,
                        space_model=space_model.display_name,
                        vehicle=space.vehicle_id.display_name,
                        vehicle_model=vehicle_model.display_name,
                    )
                )

    @api.depends("vehicle_id")
    def _compute_cargo_count(self):
        grouped = self.env["tms.cargo"]._read_group(
            [("space_allocation_id.vehicle_space_id", "in", self.ids)],
            ["space_allocation_id"],
            ["__count"],
        )
        counts = {}
        for allocation, count in grouped:
            space_id = allocation.vehicle_space_id.id
            counts[space_id] = counts.get(space_id, 0) + count
        for space in self:
            space.cargo_count = counts.get(space.id, 0)

    def action_view_cargo(self):
        """Cargo that used this slot, newest trip first."""
        self.ensure_one()
        view = self.env.ref("tms_load_planner.tms_cargo_view_list_space_history")
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Cargo"),
            "res_model": "tms.cargo",
            "view_mode": "list,form",
            "views": [(view.id, "list"), (False, "form")],
            "domain": [
                ("space_allocation_id.vehicle_space_id", "=", self.id),
            ],
        }

    def write(self, vals):
        result = super().write(vals)
        if "state" not in vals:
            return result
        if vals["state"] == "blocked":
            self._block_open_trip_allocations()
        return result

    def _block_open_trip_allocations(self):
        """Block this slot on every trip that still holds the vehicle."""
        trips = self.env["tms.order"].search(
            [
                ("vehicle_id", "in", self.vehicle_id.ids),
                ("end_trip", "=", False),
            ]
        )
        trips = trips.filtered(lambda trip: trip._occupies_vehicle_space())
        for trip in trips:
            trip._sync_space_allocations()
        allocations = self.env["tms.trip.space.allocation"].search(
            [
                ("trip_id", "in", trips.ids),
                ("vehicle_space_id", "in", self.ids),
            ]
        )
        allocations.cargo_ids.write({"space_allocation_id": False})

    def supporting_space(self, spaces):
        """The vehicle slot whose model space sits under this one."""
        self.ensure_one()
        support = self.model_space_id.supporting_space(spaces.model_space_id)
        if not support:
            return self.browse()
        return spaces.filtered(lambda space: space.model_space_id == support)[:1]
