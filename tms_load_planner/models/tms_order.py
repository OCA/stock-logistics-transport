# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare


class TmsOrder(models.Model):
    _inherit = "tms.order"

    weight_load_percent = fields.Float(
        string="Weight",
        compute="_compute_load_percent",
    )
    volume_load_percent = fields.Float(
        string="Volume",
        compute="_compute_load_percent",
    )
    space_allocation_ids = fields.One2many(
        "tms.trip.space.allocation",
        "trip_id",
        string="Space inventory",
        copy=False,
    )

    @api.depends(
        "cargo_weight",
        "capacity_weight",
        "weight_capacity_set",
        "cargo_volume",
        "capacity_volume",
        "volume_capacity_set",
    )
    def _compute_load_percent(self):
        for order in self:
            order.weight_load_percent = order._load_percent(
                order.cargo_weight,
                order.capacity_weight,
                order.weight_capacity_set,
            )
            order.volume_load_percent = order._load_percent(
                order.cargo_volume,
                order.capacity_volume,
                order.volume_capacity_set,
            )

    def _load_percent(self, allocated, capacity, capacity_set):
        if not capacity_set or not capacity:
            return 0.0
        return allocated / capacity * 100.0

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        for order in orders.filtered("vehicle_id"):
            order._sync_space_allocations()
        return orders

    def write(self, vals):
        previous_vehicles = {}
        if vals.get("vehicle_id"):
            vehicle = self.env["fleet.vehicle"].browse(vals["vehicle_id"])
            for order in self:
                order._check_vehicle_can_carry_load(vehicle)
                previous_vehicles[order.id] = order.vehicle_id
        elif "vehicle_id" in vals:
            previous_vehicles = {order.id: order.vehicle_id for order in self}
        result = super().write(vals)
        if "vehicle_id" in vals:
            for order in self:
                order._sync_space_allocations(previous_vehicles.get(order.id))
        watched = {
            "vehicle_id",
            "stage_id",
            "scheduled_date_start",
            "scheduled_date_end",
            "scheduled_duration",
            "date_start",
            "date_end",
            "duration",
            "end_trip",
        }
        if watched & set(vals):
            placed = self.cargo_ids.filtered("space_allocation_id")
            placed._check_space_load()
        return result

    def _sync_space_allocations(self, previous_vehicle=None):
        """Fill one row per space on the trip vehicle.

        A booked row is kept when the new vehicle has the same space code.
        Available rows are rebuilt. A blocked vehicle space stays blocked.
        """
        self.ensure_one()
        vehicle = self.vehicle_id
        allocations = self.space_allocation_ids
        if not vehicle:
            occupied = allocations.filtered(lambda row: row.state == "booked")
            if occupied:
                raise ValidationError(
                    self.env._(
                        "This trip still has booked spaces. "
                        "Move that cargo before removing the vehicle."
                    )
                )
            allocations.unlink()
            return
        vehicle._sync_model_spaces()
        spaces = vehicle.space_ids
        if previous_vehicle and previous_vehicle != vehicle:
            self._move_allocations_to_vehicle(allocations, spaces, vehicle)
        self._ensure_allocation_rows(spaces)

    def _move_allocations_to_vehicle(self, allocations, spaces, vehicle):
        kept = self.env["tms.trip.space.allocation"]
        for allocation in allocations.filtered(lambda row: row.state == "booked"):
            match = spaces.filtered(
                lambda space, allocation=allocation: space.code
                == allocation.vehicle_space_id.code
            )[:1]
            if not match:
                raise ValidationError(
                    self.env._(
                        "Space %(code)s is booked and %(vehicle)s has no such space.",
                        code=allocation.vehicle_space_id.code,
                        vehicle=vehicle.display_name,
                    )
                )
            if allocation.vehicle_space_id != match:
                allocation.vehicle_space_id = match
            kept |= allocation
        (allocations - kept).unlink()

    def _ensure_allocation_rows(self, spaces):
        self.ensure_one()
        missing = spaces - self.space_allocation_ids.vehicle_space_id
        if not missing:
            return
        self.env["tms.trip.space.allocation"].create(
            [
                {
                    "trip_id": self.id,
                    "vehicle_space_id": space.id,
                }
                for space in missing
            ]
        )

    def _occupies_vehicle_space(self):
        """An open trip holds its spaces. A done or cancelled trip does not."""
        self.ensure_one()
        if self.end_trip:
            return False
        stage = self.stage_id
        return bool(stage) and not stage.is_completed and not stage.fold

    def _occupancy_bounds(self):
        self.ensure_one()
        start = self.date_start or self.scheduled_date_start
        end = self.date_end or self.scheduled_date_end
        return start, end

    def _overlaps_occupancy(self, other):
        """True when both trips need the vehicle during the same time."""
        self.ensure_one()
        start, end = self._occupancy_bounds()
        other_start, other_end = other._occupancy_bounds()
        if start and other_end and start >= other_end:
            return False
        if other_start and end and other_start >= end:
            return False
        return True

    def _spaces_taken_by_other_trips(self):
        self.ensure_one()
        if not self.vehicle_id or not self._occupies_vehicle_space():
            return {}
        cargo = self.env["tms.cargo"].search(
            [
                ("order_id", "!=", self.id),
                ("order_id.vehicle_id", "=", self.vehicle_id.id),
                ("space_allocation_id", "!=", False),
                ("state", "not in", ("hold", "unassigned")),
            ]
        )
        taken = {}
        for line in cargo:
            trip = line.order_id
            if not trip._occupies_vehicle_space():
                continue
            if not self._overlaps_occupancy(trip):
                continue
            taken[line.space_allocation_id.vehicle_space_id.id] = trip
        return taken

    def _check_vehicle_can_carry_load(self, vehicle):
        """Reject a vehicle whose model cannot hold the cargo already on the trip.

        A capacity of 0, or a missing unit, is unset and does not block.
        """
        self.ensure_one()
        if not vehicle:
            return
        model = vehicle.model_id
        self._check_measure_fits(
            "weight",
            "weight_uom_id",
            model.max_weight_capacity,
            model.max_weight_uom_id,
            "payload",
        )
        self._check_measure_fits(
            "volume",
            "volume_uom_id",
            model.max_volume_capacity,
            model.max_volume_uom_id,
            "volume",
        )

    def _check_measure_fits(self, amount_field, uom_field, capacity, uom, label):
        self.ensure_one()
        if not capacity or not uom:
            return
        allocated = self._sum_cargo(amount_field, uom_field, uom)
        if float_compare(allocated, capacity, precision_digits=2) > 0:
            raise ValidationError(
                self.env._(
                    "This vehicle %(label)s is %(capacity)s %(unit)s. "
                    "The trip already carries %(allocated)s %(unit)s.",
                    label=label,
                    capacity=capacity,
                    allocated=allocated,
                    unit=uom.name,
                )
            )

    def _planner_meters(self, amount, uom, default):
        meter = self.env.ref("uom.product_uom_meter", raise_if_not_found=False)
        if not amount or not uom or not meter:
            return default
        converted = uom._compute_quantity(amount, meter)
        return converted or default

    def _planner_plan_url(self, model):
        if not model or not model.layout_image:
            return False
        stamp = 0
        if model.write_date:
            stamp = int(model.write_date.timestamp())
        return "/web/image/fleet.vehicle.model/%s/layout_image?unique=%s" % (
            model.id,
            stamp,
        )

    def _planner_box(self):
        self.ensure_one()
        model = self.vehicle_id.model_id
        return {
            "length": self._planner_meters(
                model.loading_length, model.loading_length_uom_id, 13.6
            ),
            "width": self._planner_meters(
                model.door_width, model.door_dimension_uom_id, 2.45
            ),
            "height": self._planner_meters(
                model.door_height, model.door_dimension_uom_id, 2.7
            ),
        }

    def _planner_space_vals(self, space):
        return {
            "id": space.id,
            "code": space.code,
            "pos_x": space.pos_x,
            "pos_y": space.pos_y,
            "pos_z": space.pos_z,
            "length": space.size_length,
            "width": space.size_width,
            "height": space.size_height,
        }

    def _planner_space_status(self, space, spaces, cargo_by_space):
        occupants = cargo_by_space.get(space.id)
        if occupants:
            if any(not line.is_stackable for line in occupants):
                return "top_load"
            return "stackable"
        if space.pos_z <= 0.05:
            return "empty"
        below = space.supporting_space(spaces)
        under = cargo_by_space.get(below.id) if below else None
        if under and all(line.is_stackable for line in under):
            return "empty"
        return "blocked"

    def _planner_cargo_info(self, cargo):
        labels = dict(cargo._fields["state"]._description_selection(self.env))
        return {
            "quantity": cargo.quantity,
            "uom": cargo.uom_id.name or "",
            "weight_uom": cargo.weight_uom_id.name or "",
            "volume_uom": cargo.volume_uom_id.name or "",
            "packaging": cargo.packaging or "",
            "state_label": labels.get(cargo.state, ""),
            "is_stackable": cargo.is_stackable,
        }

    def _planner_cargo_vals(self, cargo, status_by_space):
        space = cargo.space_allocation_id.vehicle_space_id
        values = {
            "id": cargo.id,
            "name": cargo.name,
            "weight": cargo.weight,
            "volume": cargo.volume,
            "sequence": cargo.sequence,
            "space": space.code or "",
            "is_stackable": cargo.is_stackable,
        }
        values.update(self._planner_cargo_info(cargo))
        if space and space.size_length and space.size_width and space.size_height:
            values.update(self._planner_space_vals(space))
            values["id"] = cargo.id
            values["status"] = status_by_space.get(space.id, "empty")
        return values

    def _allocation_color(self, cargo):
        palette = (0x2F7D4A, 0x1F6F8B, 0xC48A12, 0x8A4B6B, 0x3D6B4F, 0x245C8A)
        if not cargo:
            return 0x8D8D8D
        return palette[cargo.id % len(palette)]

    def _planner_allocation_vals(self, allocation):
        space = allocation.vehicle_space_id
        cargo = allocation.cargo_id
        values = dict(
            self._planner_space_vals(space),
            allocation_id=allocation.id,
            space_id=space.id,
            code=space.code,
            zone=space.zone,
            state=allocation.state,
            cargo_id=cargo.id or False,
            cargo_name=cargo.name or "",
            weight=cargo.weight or 0.0,
            volume=cargo.volume or 0.0,
            color=self._allocation_color(cargo) if cargo else False,
        )
        if cargo:
            values.update(self._planner_cargo_info(cargo))
        return values

    def get_load_planner_data(self):
        self.ensure_one()
        if self.vehicle_id:
            self._sync_space_allocations()
        assigned = self.cargo_ids.filtered(lambda line: line.state != "hold")
        pool = self.env["tms.cargo"].search(
            [
                ("order_id", "=", False),
                ("state", "not in", ("hold", "delivered")),
            ],
            limit=40,
            order="id desc",
        )
        box = self._planner_box()
        model = self.vehicle_id.model_id
        spaces = self.vehicle_id.space_ids
        placed = assigned.filtered("space_allocation_id")
        cargo_by_space = {}
        for line in placed:
            space = line.space_allocation_id.vehicle_space_id
            bucket = cargo_by_space.setdefault(space.id, self.env["tms.cargo"])
            cargo_by_space[space.id] = bucket | line
        taken = self._spaces_taken_by_other_trips()
        space_rows = []
        status_by_space = {}
        for space in spaces:
            status = self._planner_space_status(space, spaces, cargo_by_space)
            if not cargo_by_space.get(space.id) and space.id in taken:
                status = "taken"
            status_by_space[space.id] = status
            row = self._planner_space_vals(space)
            row["status"] = status
            space_rows.append(row)
        loose = assigned.filtered(lambda line: not line.space_allocation_id)
        return {
            "trip_id": self.id,
            "name": self.name,
            "vehicle": self.vehicle_id.display_name or "",
            "vehicle_type": model.vehicle_type or "",
            "category": model.category_id.name or "",
            "origin": self.origin_id.display_name or "",
            "destination": self.destination_id.display_name or "",
            "length": box["length"],
            "width": box["width"],
            "height": box["height"],
            "layout_image_url": self._planner_plan_url(model),
            "spaces": space_rows,
            "allocations": [
                self._planner_allocation_vals(row) for row in self.space_allocation_ids
            ],
            "assigned": [
                self._planner_cargo_vals(line, status_by_space) for line in assigned
            ],
            "loose": [
                self._planner_cargo_vals(line, status_by_space) for line in loose
            ],
            "pool": [self._planner_cargo_vals(line, status_by_space) for line in pool],
        }

    def assign_load_planner_cargo(self, cargo_id, space_id):
        self.ensure_one()
        cargo = self.env["tms.cargo"].browse(cargo_id)
        space = self.env["tms.vehicle.space"].browse(space_id)
        if not space or space.vehicle_id != self.vehicle_id:
            raise UserError(self.env._("Choose a space on this vehicle."))
        self._sync_space_allocations()
        allocation = self.space_allocation_ids.filtered(
            lambda row: row.vehicle_space_id == space
        )[:1]
        if not allocation:
            raise UserError(self.env._("Choose a space on this vehicle."))
        values = {"space_allocation_id": allocation.id}
        if cargo.order_id != self:
            values["order_id"] = self.id
        cargo.write(values)
        return self.get_load_planner_data()

    def release_load_planner_cargo(self, cargo_id):
        """Keep the cargo on this trip and clear its space."""
        self.ensure_one()
        cargo = self.env["tms.cargo"].browse(cargo_id)
        values = {"space_allocation_id": False}
        if cargo.order_id != self:
            values["order_id"] = self.id
        cargo.write(values)
        return self.get_load_planner_data()

    @api.model
    @api.model
    def _demo_place_load_planner_cargo(self):
        """Put the Volvo demo freight in a space. Leave the loose line free."""
        self._demo_loose_cargo()
        cargo = self.env.ref("tms.demo_order_3_cargo", raise_if_not_found=False)
        self._place_cargo_in_floor_space(cargo, "ROW-03-LEFT")

    @api.model
    def _demo_loose_cargo(self):
        """Add an unplaced line on the Volvo demo trip when the vehicle can take it."""
        xmlid = "tms_load_planner.demo_order_3_loose_cargo"
        if self.env.ref(xmlid, raise_if_not_found=False):
            return
        trip = self.env.ref("tms.demo_order_3", raise_if_not_found=False)
        if not trip:
            return
        try:
            cargo = self.env["tms.cargo"].create(
                {
                    "order_id": trip.id,
                    "name": "Loose cartons",
                    "quantity": 4,
                    "uom_id": self.env.ref("uom.product_uom_unit").id,
                    "weight": 80,
                    "weight_uom_id": self.env.ref("uom.product_uom_kgm").id,
                    "volume": 0.5,
                    "volume_uom_id": self.env.ref("uom.product_uom_cubic_meter").id,
                    "packaging": "Cartons",
                }
            )
        except ValidationError:
            return
        self.env["ir.model.data"].create(
            {
                "module": "tms_load_planner",
                "name": "demo_order_3_loose_cargo",
                "model": "tms.cargo",
                "res_id": cargo.id,
                "noupdate": True,
            }
        )

    def _place_cargo_in_floor_space(self, cargo, code):
        """Book a floor space for cargo that does not have one yet."""
        if not cargo or cargo.space_allocation_id or not cargo.order_id:
            return False
        trip = cargo.order_id
        trip._sync_space_allocations()
        allocation = trip.space_allocation_ids.filtered(
            lambda row, code=code: row.vehicle_space_id.code == code
            and row.vehicle_space_id.pos_z <= 0.05
        )[:1]
        if not allocation:
            return False
        cargo.space_allocation_id = allocation
        return True

    def action_open_load_planner(self):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "tms_load_planner",
            "name": self.env._("Load planner"),
            "context": {"active_id": self.id},
        }
