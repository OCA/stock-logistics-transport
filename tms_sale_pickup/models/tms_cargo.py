# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare

LOCKED_SOLD_FIELDS = {
    "name",
    "quantity",
    "uom_id",
    "weight",
    "weight_uom_id",
    "volume",
    "volume_uom_id",
    "packaging",
}


class TMSCargo(models.Model):
    _inherit = "tms.cargo"

    parent_id = fields.Many2one(
        "tms.cargo",
        string="Sold cargo",
        ondelete="cascade",
        index=True,
        copy=False,
    )
    pickup_ids = fields.One2many("tms.cargo", "parent_id", string="Pickups")
    sold_locked = fields.Boolean(copy=False)
    pickup_quantity = fields.Float(compute="_compute_pickup_delta")
    pickup_weight = fields.Float(compute="_compute_pickup_delta")
    pickup_volume = fields.Float(compute="_compute_pickup_delta")
    quantity_delta = fields.Float(compute="_compute_pickup_delta")
    weight_delta = fields.Float(compute="_compute_pickup_delta")
    volume_delta = fields.Float(compute="_compute_pickup_delta")
    has_discrepancy = fields.Boolean(compute="_compute_pickup_delta")

    @api.depends(
        "quantity",
        "weight",
        "weight_uom_id",
        "volume",
        "volume_uom_id",
        "pickup_ids.quantity",
        "pickup_ids.weight",
        "pickup_ids.weight_uom_id",
        "pickup_ids.volume",
        "pickup_ids.volume_uom_id",
    )
    def _compute_pickup_delta(self):
        for cargo in self:
            cargo.pickup_quantity = sum(cargo.pickup_ids.mapped("quantity"))
            cargo.pickup_weight = cargo._sum_pickups("weight", "weight_uom_id")
            cargo.pickup_volume = cargo._sum_pickups("volume", "volume_uom_id")
            cargo.quantity_delta = cargo.pickup_quantity - cargo.quantity
            cargo.weight_delta = cargo.pickup_weight - cargo.weight
            cargo.volume_delta = cargo.pickup_volume - cargo.volume
            cargo.has_discrepancy = bool(cargo.pickup_ids) and any(
                float_compare(delta, 0.0, precision_rounding=0.01)
                for delta in (
                    cargo.quantity_delta,
                    cargo.weight_delta,
                    cargo.volume_delta,
                )
            )

    def _sum_pickups(self, amount_field, uom_field):
        self.ensure_one()
        target = self[uom_field]
        total = 0.0
        for pickup in self.pickup_ids:
            amount = pickup[amount_field]
            uom = pickup[uom_field]
            if target and uom:
                total += uom._compute_quantity(amount, target)
            else:
                total += amount
        return total

    def _link_sale_line_from_trip(self):
        sold = self.filtered(lambda cargo: not cargo.parent_id)
        return super(TMSCargo, sold)._link_sale_line_from_trip()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            parent_id = vals.get("parent_id")
            if parent_id and not vals.get("order_id"):
                parent = self.browse(parent_id)
                vals["order_id"] = parent.order_id.id
        records = super(TMSCargo, self.with_context(skip_cargo_sale_sync=True)).create(
            vals_list
        )
        sold = records.filtered(lambda cargo: not cargo.parent_id)
        sold._link_sale_line_from_trip()
        sold._link_trip_from_sale_line()
        lines = (sold | records.parent_id).sudo().sale_line_id
        if lines:
            lines._sync_tms_weight_factor_from_cargo()
            lines._sync_tms_volume_factor_from_cargo()
        return records

    def write(self, vals):
        if LOCKED_SOLD_FIELDS & set(vals) and self.filtered("sold_locked"):
            raise UserError(
                self.env._(
                    "Sold cargo is frozen once the sale is confirmed. "
                    "Record the difference on a pickup line."
                )
            )
        if "order_id" in vals:
            pickups = self.filtered(lambda cargo: not cargo.parent_id).pickup_ids
            if pickups:
                pickups.write({"order_id": vals["order_id"]})
        result = super().write(vals)
        if not self.env.context.get("skip_cargo_sale_sync") and {
            "volume",
            "volume_uom_id",
            "sale_line_id",
            "order_id",
        } & set(vals):
            self.sale_line_id._sync_tms_volume_factor_from_cargo()
        return result

    @api.constrains("parent_id", "order_id")
    def _check_pickup_trip(self):
        for cargo in self:
            parent = cargo.parent_id
            if not parent:
                continue
            if parent.parent_id:
                raise ValidationError(
                    self.env._(
                        "Record the pickup on the sold cargo, not on another pickup."
                    )
                )
            if cargo.order_id != parent.order_id:
                raise ValidationError(
                    self.env._("A pickup stays on the trip of the cargo that was sold.")
                )
