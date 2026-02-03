# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class TmsOrderFromStops(models.TransientModel):
    _name = "tms.order.from.stops"
    _inherit = "capacity.utilization.mixin"
    _description = "Create TMS Order from Selected Stops"

    stop_ids = fields.Many2many(
        comodel_name="tms.order.stop",
        string="Selected Stops",
        readonly=True,
    )
    stop_count = fields.Integer(
        compute="_compute_stop_count",
        string="Number of Stops",
    )
    tms_team_id = fields.Many2one(
        comodel_name="tms.team",
        string="TMS Team",
        required=True,
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
        string="Origin",
        domain="[('tms_location', '=', True)]",
    )
    destination_id = fields.Many2one(
        comodel_name="res.partner",
        string="Destination",
        domain="[('tms_location', '=', True)]",
    )
    return_to_origin = fields.Boolean(
        string="Retornar à Origem",
        default=False,
        help="Se marcado, o destino final será o mesmo local de origem",
    )
    scheduled_date_start = fields.Datetime(
        string="Scheduled Start Date",
    )

    # Cargo totals for capacity utilization
    total_weight = fields.Float(
        string="Total Weight (kg)",
        compute="_compute_stop_totals",
    )
    total_volume = fields.Float(
        string="Total Volume (m³)",
        compute="_compute_stop_totals",
    )

    @api.depends("stop_ids", "stop_ids.weight", "stop_ids.volume")
    def _compute_stop_totals(self):
        for wizard in self:
            wizard.total_weight = sum(wizard.stop_ids.mapped("weight"))
            wizard.total_volume = sum(wizard.stop_ids.mapped("volume"))

    @api.depends("vehicle_id")
    def _compute_capacity_from_vehicle(self):
        return super()._compute_capacity_from_vehicle()

    @api.depends("vehicle_id", "total_weight", "total_volume")
    def _compute_utilization(self):
        return super()._compute_utilization()

    @api.depends("stop_ids")
    def _compute_stop_count(self):
        for wizard in self:
            wizard.stop_count = len(wizard.stop_ids)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # Get stop_ids from context
        if self._context.get("active_model") == "tms.order.stop":
            stop_ids = self._context.get("active_ids", [])
            if stop_ids:
                res["stop_ids"] = [(6, 0, stop_ids)]
        elif self._context.get("default_stop_ids"):
            res["stop_ids"] = [(6, 0, self._context["default_stop_ids"])]
        return res

    @api.onchange("tms_team_id")
    def _onchange_tms_team_id(self):
        """Fill origin/destination from team defaults."""
        if self.tms_team_id:
            if self.tms_team_id.default_origin_location_id:
                self.origin_id = self.tms_team_id.default_origin_location_id
            if self.tms_team_id.default_destination_location_id:
                self.destination_id = self.tms_team_id.default_destination_location_id

    @api.onchange("return_to_origin", "origin_id")
    def _onchange_return_to_origin(self):
        """Set destination to origin when return_to_origin is checked."""
        if self.return_to_origin and self.origin_id:
            self.destination_id = self.origin_id
        elif self.return_to_origin and not self.origin_id:
            # Checkbox marked but no origin yet - keep destination empty
            self.destination_id = False

    @api.onchange("destination_id")
    def _onchange_destination_id(self):
        """Sync return_to_origin checkbox based on destination value."""
        if self.destination_id and self.origin_id:
            self.return_to_origin = self.destination_id == self.origin_id
        elif not self.destination_id:
            self.return_to_origin = False

    def action_create_order(self):
        """Create TMS order and assign stops."""
        self.ensure_one()

        # Validate that stops are not already allocated
        allocated = self.stop_ids.filtered(lambda s: s.order_id)
        if allocated:
            raise UserError(
                _("The following stops are already allocated to an order: %s")
                % ", ".join(allocated.mapped("display_name"))
            )

        if not self.stop_ids:
            raise UserError(_("No stops selected."))

        # Create order
        order_vals = {
            "tms_team_id": self.tms_team_id.id,
            "origin_id": self.origin_id.id if self.origin_id else False,
            "destination_id": self.destination_id.id if self.destination_id else False,
            "vehicle_id": self.vehicle_id.id if self.vehicle_id else False,
            "driver_id": self.driver_id.id if self.driver_id else False,
            "scheduled_date_start": self.scheduled_date_start,
        }
        order = self.env["tms.order"].create(order_vals)

        # Assign stops to order with sequence
        for idx, stop in enumerate(self.stop_ids.sorted("sequence"), start=1):
            stop.write(
                {
                    "order_id": order.id,
                    "sequence": idx * 10,
                }
            )

        # Return action to open created order
        return {
            "type": "ir.actions.act_window",
            "name": _("TMS Order"),
            "res_model": "tms.order",
            "res_id": order.id,
            "view_mode": "form",
            "target": "current",
        }
