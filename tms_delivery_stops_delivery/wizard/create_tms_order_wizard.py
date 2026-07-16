# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class TMSOrderFromPickings(models.TransientModel):
    _name = "tms.order.from.pickings"
    _description = "Create or Assign TMS Order from Pickings"

    mode = fields.Selection(
        selection=[
            ("new_order", "Create New TMS Order"),
            ("manual_plan", "Create Manual Plan"),
            ("existing_order", "Assign to Existing TMS Order"),
        ],
        default="new_order",
        required=True,
    )
    picking_ids = fields.Many2many(
        comodel_name="stock.picking",
        string="Pickings",
        required=True,
    )
    tms_team_id = fields.Many2one(
        comodel_name="tms.team",
        string="TMS Team",
    )
    existing_order_id = fields.Many2one(
        comodel_name="tms.order",
        string="Existing TMS Order",
    )
    vehicle_id = fields.Many2one(
        comodel_name="fleet.vehicle",
        string="Vehicle",
    )
    driver_id = fields.Many2one(
        comodel_name="tms.driver",
        string="Driver",
    )
    origin_id = fields.Many2one(
        comodel_name="res.partner",
        string="Origin Location",
        domain="[('tms_location', '=', True)]",
        context={"default_tms_location": True},
    )
    destination_id = fields.Many2one(
        comodel_name="res.partner",
        string="Destination Location",
        domain="[('tms_location', '=', True)]",
        context={"default_tms_location": True},
    )
    scheduled_date_start = fields.Datetime(
        string="Scheduled Start",
    )
    description = fields.Text()

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids", [])
        if active_model == "stock.picking" and active_ids:
            res["picking_ids"] = [(6, 0, active_ids)]
        return res

    @api.onchange("picking_ids")
    def _onchange_picking_ids(self):
        if not self.picking_ids:
            return
        missing_stops = self.picking_ids.filtered(lambda p: not p.tms_stop_id)
        if missing_stops:
            return {
                "warning": {
                    "title": _("Missing TMS Stops"),
                    "message": _("Some pickings have no TMS stop and will be ignored."),
                }
            }

    def action_create_order(self):
        self.ensure_one()
        pickings = self.picking_ids.filtered(lambda p: p.tms_stop_id)
        if not pickings:
            raise UserError(_("All selected pickings must have a TMS stop."))

        if self.mode == "existing_order":
            if not self.existing_order_id:
                raise UserError(_("Please select an existing TMS order."))
            order = self.existing_order_id
        else:
            order_vals = {
                "tms_team_id": self.tms_team_id.id,
                "vehicle_id": self.vehicle_id.id,
                "driver_id": self.driver_id.id,
                "origin_id": self.origin_id.id,
                "destination_id": self.destination_id.id,
                "scheduled_date_start": self.scheduled_date_start,
                "description": self.description,
            }
            if not self.tms_team_id:
                raise UserError(_("TMS Team is required."))
            order = self.env["tms.order"].create(order_vals)

        stops = pickings.mapped("tms_stop_id")
        stops.write({"order_id": order.id})
        if self.mode == "manual_plan":
            stops.write({"state": "draft"})

        return {
            "type": "ir.actions.act_window",
            "name": _("TMS Order"),
            "res_model": "tms.order",
            "view_mode": "form",
            "res_id": order.id,
            "target": "current",
        }
