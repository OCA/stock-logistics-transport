# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class TMSCargo(models.Model):
    _name = "tms.cargo"
    _description = "Transport Cargo"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    name = fields.Char(string="Description", required=True)
    order_id = fields.Many2one("tms.order", string="Trip", ondelete="set null")
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
    state = fields.Selection(
        [
            ("planned", "Planned"),
            ("loaded", "Loaded"),
            ("delivered", "Delivered"),
        ],
        default="planned",
        required=True,
    )

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

    @api.model_create_multi
    def create(self, vals_list):
        cargos = super().create(vals_list)
        cargos.order_id._sync_loaded_stage()
        return cargos

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
