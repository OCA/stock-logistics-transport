# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError


class TMSCargoSplit(models.TransientModel):
    _name = "tms.cargo.split"
    _description = "Split Cargo Line"

    cargo_id = fields.Many2one("tms.cargo", required=True)
    quantity = fields.Float(string="Pieces")
    weight = fields.Float()
    volume = fields.Float()

    def action_apply(self):
        self.ensure_one()
        cargo = self.cargo_id
        cargo._check_line_is_open()
        if self.quantity <= 0 and self.weight <= 0 and self.volume <= 0:
            raise UserError(
                self.env._("Enter the pieces, weight, or volume to split off.")
            )
        if cargo.quantity and self.quantity >= cargo.quantity:
            raise UserError(
                self.env._("Leave part of the quantity on the original line.")
            )
        if self.weight > cargo.weight or self.volume > cargo.volume:
            raise UserError(
                self.env._("The split cannot exceed the weight or volume of the line.")
            )
        ratio = (self.quantity / cargo.quantity) if cargo.quantity else 0.0
        meters = cargo.loading_meters * ratio
        values = {
            "name": cargo.name,
            "order_id": cargo.order_id.id,
            "quantity": self.quantity,
            "uom_id": cargo.uom_id.id,
            "weight": self.weight,
            "weight_uom_id": cargo.weight_uom_id.id,
            "volume": self.volume,
            "volume_uom_id": cargo.volume_uom_id.id,
            "shipment_unit": cargo.shipment_unit,
            "is_stackable": cargo.is_stackable,
            "loading_meters": meters,
            "state": "planned",
        }
        if "sale_line_id" in cargo._fields and cargo.sale_line_id:
            values["sale_line_id"] = cargo.sale_line_id.id
        if "parent_id" in cargo._fields and cargo.parent_id:
            values["parent_id"] = cargo.parent_id.id
        self.env["tms.cargo"].create(values)
        cargo.write(
            {
                "quantity": cargo.quantity - self.quantity,
                "weight": cargo.weight - self.weight,
                "volume": cargo.volume - self.volume,
                "loading_meters": cargo.loading_meters - meters,
            }
        )
        return {"type": "ir.actions.act_window_close"}


class TMSCargoReassign(models.TransientModel):
    _name = "tms.cargo.reassign"
    _description = "Reassign Cargo"

    cargo_id = fields.Many2one("tms.cargo", required=True)
    trip_id = fields.Many2one(
        "tms.order",
        string="Trip",
        required=True,
        domain="[('id', 'in', allowed_trip_ids)]",
    )
    allowed_trip_ids = fields.Many2many("tms.order", compute="_compute_allowed_trips")

    @api.depends("cargo_id", "cargo_id.order_id")
    def _compute_allowed_trips(self):
        for wizard in self:
            domain = [
                ("start_trip", "=", False),
                ("end_trip", "=", False),
                ("transport_type", "=", "cargo"),
            ]
            if wizard.cargo_id.order_id:
                domain.append(("id", "!=", wizard.cargo_id.order_id.id))
            wizard.allowed_trip_ids = self.env["tms.order"].search(domain)

    def action_apply(self):
        self.ensure_one()
        cargo = self.cargo_id
        cargo._check_line_is_open()
        if self.trip_id.start_trip or self.trip_id.end_trip:
            raise UserError(self.env._("That trip has already started."))
        cargo.order_id = self.trip_id
        if cargo.state == "unassigned":
            cargo.state = "planned"
        return {"type": "ir.actions.act_window_close"}


class TMSCargoSwap(models.TransientModel):
    _name = "tms.cargo.swap"
    _description = "Swap Cargo Assignment"

    cargo_id = fields.Many2one("tms.cargo", required=True)
    candidate_id = fields.Many2one(
        "tms.cargo",
        string="Lighter cargo",
        required=True,
        domain="[('id', 'in', candidate_ids)]",
    )
    candidate_ids = fields.Many2many("tms.cargo", compute="_compute_candidates")

    @api.depends("cargo_id")
    def _compute_candidates(self):
        for wizard in self:
            cargo = wizard.cargo_id
            wizard.candidate_ids = cargo._swap_candidates() if cargo else cargo

    def action_apply(self):
        self.ensure_one()
        cargo = self.cargo_id
        other = self.candidate_id
        (cargo | other)._check_line_is_open()
        if other not in cargo._swap_candidates():
            raise UserError(
                self.env._(
                    "Swap with a lighter planned line headed to the same destination."
                )
            )
        source = cargo.order_id
        target = other.order_id
        cargo.order_id = target
        other.order_id = source
        return {"type": "ir.actions.act_window_close"}


class TMSCargoCondition(models.TransientModel):
    _name = "tms.cargo.condition"
    _description = "Cargo Condition"

    cargo_id = fields.Many2one("tms.cargo", required=True)
    note = fields.Text(string="Condition note")
    attachment_ids = fields.Many2many("ir.attachment", string="Photos")

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        cargo = self.env["tms.cargo"].browse(values.get("cargo_id"))
        if cargo and "note" in fields_list and not values.get("note"):
            values["note"] = cargo.condition_note
        if cargo and "attachment_ids" in fields_list and cargo.condition_attachment_ids:
            values["attachment_ids"] = [(6, 0, cargo.condition_attachment_ids.ids)]
        return values

    def action_apply(self):
        self.ensure_one()
        cargo = self.cargo_id
        self.attachment_ids.write({"res_model": "tms.cargo", "res_id": cargo.id})
        cargo.write(
            {
                "condition_note": self.note,
                "condition_attachment_ids": [(6, 0, self.attachment_ids.ids)],
            }
        )
        return {"type": "ir.actions.act_window_close"}
