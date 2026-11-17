# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


CONTAINER_TYPES = [
    ("20dry", "20' Dry"),
    ("40dry", "40' Dry"),
    ("40hc", "40' High Cube"),
    ("45hc", "45' High Cube"),
    ("20reefer", "20' Reefer"),
    ("40reefer", "40' Reefer"),
]
ULD_TYPES = [
    ("ake", "AKE (LD3)"),
    ("akh", "AKH (LD3-45)"),
    ("aap", "AAP (LD9)"),
    ("pmc", "PMC (LD7 pallet)"),
    ("pag", "PAG (LD7 pallet)"),
    ("pla", "PLA (LD11)"),
]
CONTAINER_MODES = {"fcl"}
ULD_MODES = {"back_to_back"}
# Internal volume in m³ and payload in kg for a shared shell.
SHELL_CAPACITY = {
    "20dry": (33.2, 21770.0),
    "40dry": (67.7, 26480.0),
    "40hc": (76.3, 26460.0),
    "45hc": (86.0, 25600.0),
    "20reefer": (28.3, 21000.0),
    "40reefer": (59.3, 26000.0),
    "ake": (4.3, 1588.0),
    "akh": (3.5, 1134.0),
    "aap": (10.0, 4626.0),
    "pmc": (11.5, 6800.0),
    "pag": (11.5, 6800.0),
    "pla": (7.0, 3175.0),
}


class TMSCargo(models.Model):
    _name = "tms.cargo"
    _description = "Transport Cargo"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    name = fields.Char(string="Description", required=True, tracking=True)
    shipment_unit = fields.Selection(
        [
            ("cargo", "Cargo"),
            ("container", "Container"),
            ("uld", "ULD"),
        ],
        default="cargo",
        required=True,
    )
    container_type = fields.Selection(CONTAINER_TYPES, string="Container type")
    container_number = fields.Char(string="Container number")
    seal_number = fields.Char(string="Seal")
    uld_type = fields.Selection(ULD_TYPES, string="ULD type")
    uld_number = fields.Char(string="ULD number")
    holding_id = fields.Many2one(
        "tms.cargo",
        string="Loaded in",
        ondelete="set null",
        index=True,
        copy=False,
    )
    content_ids = fields.One2many("tms.cargo", "holding_id", string="Contents")
    order_id = fields.Many2one(
        "tms.order",
        string="Trip",
        ondelete="set null",
        tracking=True,
    )
    origin_id = fields.Many2one(related="order_id.origin_id")
    destination_id = fields.Many2one(related="order_id.destination_id")
    locked = fields.Boolean(compute="_compute_locked")
    movable = fields.Boolean(compute="_compute_locked")
    quantity = fields.Float(string="Pieces", default=1.0)
    uom_id = fields.Many2one(
        "uom.uom",
        string="Unit",
        default=lambda self: self.env.ref(
            "uom.product_uom_unit", raise_if_not_found=False
        ),
    )
    weight = fields.Float()
    weight_uom_id = fields.Many2one(
        "uom.uom",
        string="Weight unit",
        domain=lambda self: self.env["res.config.settings"]._weight_domain(),
        default=lambda self: self.env.ref(
            "uom.product_uom_kgm", raise_if_not_found=False
        ),
    )
    volume = fields.Float()
    volume_uom_id = fields.Many2one(
        "uom.uom",
        string="Volume unit",
        domain=lambda self: self.env["res.config.settings"]._volume_domain(),
        default=lambda self: self.env.ref(
            "uom.product_uom_cubic_meter", raise_if_not_found=False
        ),
    )
    packaging = fields.Char()
    is_stackable = fields.Boolean(
        string="Stackable",
        default=True,
        help="A top-load line keeps the space above it empty, so it uses "
        "twice the floor of a stackable line.",
    )
    loading_meters = fields.Float(
        string="Loading meters",
        help="Floor length this line uses when it can be stacked.",
    )
    condition_note = fields.Text(string="Condition note")
    condition_attachment_ids = fields.Many2many(
        "ir.attachment",
        "tms_cargo_condition_attachment_rel",
        "cargo_id",
        "attachment_id",
        string="Condition photos",
    )
    state = fields.Selection(
        [
            ("planned", "Planned"),
            ("loaded", "Loaded"),
            ("delivered", "Delivered"),
            ("hold", "On hold"),
            ("unassigned", "Unassigned"),
        ],
        default="planned",
        required=True,
        tracking=True,
    )

    @api.depends("order_id.start_trip", "order_id.end_trip", "state")
    def _compute_locked(self):
        open_states = ("planned", "hold", "unassigned")
        for cargo in self:
            trip = cargo.order_id
            cargo.locked = bool(trip.start_trip or trip.end_trip)
            cargo.movable = not cargo.locked and cargo.state in open_states

    def write(self, vals):
        if "order_id" in vals and not self.env.context.get("skip_cargo_sale_sync"):
            destination = self.env["tms.order"].browse(vals["order_id"])
            started = (self.order_id | destination).filtered(
                lambda trip: trip.start_trip or trip.end_trip
            )
            if started:
                raise UserError(
                    self.env._("Cargo cannot move once a trip has started.")
                )
        orders = self.order_id
        result = super().write(vals)
        (orders | self.order_id)._sync_loaded_stage()
        return result

    @api.model
    def _shipment_unit_from_mode(self, cargo_mode):
        if cargo_mode in CONTAINER_MODES:
            return "container"
        if cargo_mode in ULD_MODES:
            return "uld"
        return "cargo"

    @api.model
    def _shipment_name_from_vals(self, vals):
        unit = vals.get("shipment_unit") or "cargo"
        if unit == "container":
            label = dict(CONTAINER_TYPES).get(vals.get("container_type"), "")
            number = vals.get("container_number") or ""
            return " ".join(part for part in (label, number) if part)
        if unit == "uld":
            label = dict(ULD_TYPES).get(vals.get("uld_type"), "")
            number = vals.get("uld_number") or ""
            return " ".join(part for part in (label, number) if part)
        return vals.get("name") or ""

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name"):
                vals["name"] = self._shipment_name_from_vals(vals) or self.env._(
                    "Shipment"
                )
            if not vals.get("state"):
                vals["state"] = "planned"
        cargos = super().create(vals_list)
        cargos.order_id._sync_loaded_stage()
        return cargos

    def _shell_capacity(self):
        """Return (volume m³, weight kg) for a container or ULD shell."""
        self.ensure_one()
        return SHELL_CAPACITY.get(self.container_type or self.uld_type)

    def _measure_in(self, cargos, amount_field, uom_field, target_uom):
        total = 0.0
        for cargo in cargos:
            amount = cargo[amount_field]
            uom = cargo[uom_field]
            if not amount:
                continue
            if target_uom and uom:
                total += uom._compute_quantity(amount, target_uom)
            else:
                total += amount
        return total

    def _shell_can_hold(self, cargos):
        """True when the added freight fits this container or ULD."""
        self.ensure_one()
        capacity = self._shell_capacity()
        if not capacity:
            return True
        cap_volume, cap_weight = capacity
        cubic_meter = self.env.ref(
            "uom.product_uom_cubic_meter", raise_if_not_found=False
        )
        kilogram = self.env.ref("uom.product_uom_kgm", raise_if_not_found=False)
        contents = self.content_ids
        volume = self._measure_in(
            contents, "volume", "volume_uom_id", cubic_meter
        ) + self._measure_in(cargos, "volume", "volume_uom_id", cubic_meter)
        weight = self._measure_in(
            contents, "weight", "weight_uom_id", kilogram
        ) + self._measure_in(cargos, "weight", "weight_uom_id", kilogram)
        if volume and volume > cap_volume:
            return False
        if weight and weight > cap_weight:
            return False
        return True

    def _check_line_is_open(self):
        started = self.order_id.filtered(lambda trip: trip.start_trip or trip.end_trip)
        if started:
            raise UserError(self.env._("Cargo cannot move once a trip has started."))
        if self.filtered(lambda cargo: cargo.state == "delivered"):
            raise UserError(self.env._("Delivered cargo stays on its trip."))

    def _loading_meters_from_pallets(self):
        """One pallet occupies 0.4 loading meters on a standard trailer."""
        self.ensure_one()
        pallet = self.env.ref("tms.uom_pallet", raise_if_not_found=False)
        if not pallet or self.uom_id != pallet:
            return 0.0
        return self.quantity * 0.4

    def _weight_in_kg(self):
        self.ensure_one()
        kilogram = self.env.ref("uom.product_uom_kgm", raise_if_not_found=False)
        if kilogram and self.weight_uom_id:
            return self.weight_uom_id._compute_quantity(self.weight, kilogram)
        return self.weight

    def action_put_on_hold(self):
        self._check_line_is_open()
        blocked = self.filtered(
            lambda cargo: cargo.state != "planned" or not cargo.order_id
        )
        if blocked:
            raise UserError(
                self.env._("Only planned cargo on a trip can be put on hold.")
            )
        self.state = "hold"

    def action_release_hold(self):
        self._check_line_is_open()
        self.filtered(lambda cargo: cargo.state == "hold").state = "planned"

    def action_return_to_pool(self):
        """Drop the trip and keep the sale line, ready for a later assignment."""
        self._check_line_is_open()
        self.write({"order_id": False, "state": "unassigned"})

    def action_toggle_top_load(self):
        self._check_line_is_open()
        for cargo in self:
            stackable = not cargo.is_stackable
            values = {"is_stackable": stackable}
            if not stackable and not cargo.loading_meters:
                meters = cargo._loading_meters_from_pallets()
                if meters:
                    values["loading_meters"] = meters
            cargo.write(values)

    def action_split_line(self):
        self.ensure_one()
        self._check_line_is_open()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Split Line"),
            "res_model": "tms.cargo.split",
            "view_mode": "form",
            "target": "new",
            "context": {"default_cargo_id": self.id},
        }

    def action_reassign(self):
        self.ensure_one()
        self._check_line_is_open()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Reassign"),
            "res_model": "tms.cargo.reassign",
            "view_mode": "form",
            "target": "new",
            "context": {"default_cargo_id": self.id},
        }

    def action_swap(self):
        self.ensure_one()
        self._check_line_is_open()
        if not self.order_id:
            raise UserError(self.env._("Assign the cargo to a trip before swapping."))
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Swap Assignment"),
            "res_model": "tms.cargo.swap",
            "view_mode": "form",
            "target": "new",
            "context": {"default_cargo_id": self.id},
        }

    def action_attach_condition(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Proof of condition"),
            "res_model": "tms.cargo.condition",
            "view_mode": "form",
            "target": "new",
            "context": {"default_cargo_id": self.id},
        }

    def _swap_candidates(self):
        """Lighter planned cargo headed to the same destination."""
        self.ensure_one()
        trip = self.order_id
        if not trip or not trip.destination_id:
            return self.browse()
        own_weight = self._weight_in_kg()
        candidates = self.search(
            [
                ("id", "!=", self.id),
                ("order_id", "!=", trip.id),
                ("order_id.destination_id", "=", trip.destination_id.id),
                ("order_id.start_trip", "=", False),
                ("order_id.end_trip", "=", False),
                ("state", "=", "planned"),
            ]
        )
        return candidates.filtered(lambda cargo: cargo._weight_in_kg() < own_weight)

    def unlink(self):
        orders = self.order_id
        result = super().unlink()
        orders._sync_loaded_stage()
        return result

    @api.constrains("order_id")
    def _check_cargo_vehicle(self):
        for cargo in self:
            vehicle = cargo.order_id.vehicle_id
            if vehicle and vehicle.operation != "cargo":
                raise ValidationError(
                    self.env._(
                        "Cargo can be added only when the vehicle manages cargo."
                    )
                )
