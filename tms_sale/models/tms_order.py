# Copyright (C) 2019 Brian McMaster
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models
from odoo.exceptions import UserError


TRANSIT_VEHICLE_TYPES = {
    "air": ("plane",),
    "water": ("boat",),
    "road": ("truck", "van", "bus", "car"),
    "rail": (),
}


class TMSOrder(models.Model):
    _inherit = "tms.order"

    sale_id = fields.Many2one("sale.order", copy=False)
    sale_line_id = fields.Many2one("sale.order.line", copy=False)
    seat_ticket_ids = fields.One2many("seat.ticket", "tms_order_id")
    seat_sale_order_ids = fields.Many2many(
        "sale.order",
        compute="_compute_seat_sale_orders",
    )
    seat_sale_order_count = fields.Integer(
        compute="_compute_seat_sale_orders",
        string="Sales Orders",
    )
    cargo_sale_order_ids = fields.Many2many(
        "sale.order",
        compute="_compute_cargo_sale_orders",
        string="Cargo Sales",
    )
    cargo_sale_order_count = fields.Integer(compute="_compute_cargo_sale_orders")
    shipment_line_ids = fields.Many2many(
        "tms.cargo",
        compute="_compute_shipment_lines",
        string="Shipment lines",
    )
    shipment_line_count = fields.Integer(compute="_compute_shipment_lines")

    @api.depends("seat_ticket_ids.sale_line_id.order_id")
    def _compute_seat_sale_orders(self):
        for order in self:
            sale_orders = order.seat_ticket_ids.mapped("sale_order_id")
            order.seat_sale_order_ids = sale_orders
            order.seat_sale_order_count = len(sale_orders)

    def action_view_seat_sale_orders(self):
        self.ensure_one()
        sale_orders = self.seat_sale_order_ids
        action = self.env["ir.actions.act_window"]._for_xml_id("sale.action_orders")
        if len(sale_orders) > 1:
            action["domain"] = [("id", "in", sale_orders.ids)]
        elif len(sale_orders) == 1:
            action["views"] = [(self.env.ref("sale.view_order_form").id, "form")]
            action["res_id"] = sale_orders.id
        else:
            action = {"type": "ir.actions.act_window_close"}
        return action

    def _sync_boarded_stage(self):
        boarded = self.env.ref("tms.tms_stage_order_boarded", raise_if_not_found=False)
        confirmed = self.env.ref(
            "tms.tms_stage_order_confirmed", raise_if_not_found=False
        )
        if not boarded or not confirmed:
            return
        for order in self:
            if order._trip_operation() != "passenger":
                continue
            sold = order.seat_ticket_ids.filtered("sale_line_id")
            all_boarded = bool(sold) and all(ticket.boarded for ticket in sold)
            if all_boarded and order.stage_id == confirmed:
                order.stage_id = boarded
            elif not all_boarded and order.stage_id == boarded:
                order.stage_id = confirmed

    def _check_stage_before_start(self):
        result = super()._check_stage_before_start()
        boarded = self.env.ref("tms.tms_stage_order_boarded", raise_if_not_found=False)
        for order in self:
            if order._trip_operation() != "passenger" or not boarded:
                continue
            sold = order.seat_ticket_ids.filtered("sale_line_id")
            if sold and order.stage_id != boarded:
                raise UserError(
                    self.env._("Board the passengers before starting this trip.")
                )
        return result

    @api.depends(
        "tms_team_id",
        "tms_team_id.vehicle_ids",
        "transport_type",
        "sale_line_id.product_id.transit_mode",
        "cargo_ids.sale_line_id.product_id.transit_mode",
    )
    def _compute_vehicle_ids_domain(self):
        super()._compute_vehicle_ids_domain()
        for order in self:
            mode = order.sale_line_id.product_id.product_tmpl_id.transit_mode
            if not mode:
                modes = set(
                    order.cargo_ids.sale_line_id.product_id.product_tmpl_id.mapped(
                        "transit_mode"
                    )
                )
                mode = modes.pop() if len(modes) == 1 else False
            allowed = TRANSIT_VEHICLE_TYPES.get(mode)
            if not allowed:
                continue
            order.vehicle_ids_domain = order.vehicle_ids_domain.filtered(
                lambda vehicle, types=allowed: vehicle.model_id.vehicle_type in types
            )

    @api.depends("cargo_ids.sale_line_id")
    def _compute_shipment_lines(self):
        for order in self:
            lines = order.cargo_ids.filtered("sale_line_id")
            if "parent_id" in lines._fields:
                lines = lines.filtered(lambda cargo: not cargo.parent_id)
            order.shipment_line_ids = lines
            order.shipment_line_count = len(lines)

    def action_view_shipment_lines(self):
        self.ensure_one()
        lines = self.shipment_line_ids
        form_view = self.env.ref("tms_sale.tms_shipment_line_view_form")
        list_view = self.env.ref("tms_sale.tms_shipment_line_view_list")
        action = {
            "type": "ir.actions.act_window",
            "name": self.env._("Shipment lines"),
            "res_model": "tms.cargo",
            "target": "current",
            "context": {"create": False},
        }
        if len(lines) == 1:
            action["view_mode"] = "form"
            action["views"] = [(form_view.id, "form")]
            action["res_id"] = lines.id
        else:
            action["view_mode"] = "list,form"
            action["views"] = [
                (list_view.id, "list"),
                (form_view.id, "form"),
            ]
            action["domain"] = [("id", "in", lines.ids)]
        return action

    @api.depends("sale_id", "sale_line_id.order_id", "cargo_ids.sale_line_id.order_id")
    def _compute_cargo_sale_orders(self):
        for order in self:
            sales = order.sale_id | order.sale_line_id.order_id
            sales |= order.cargo_ids.sale_line_id.order_id
            order.cargo_sale_order_ids = sales
            order.cargo_sale_order_count = len(sales)

    def _sale_link_for_split(self):
        """Keep the sale on the new trip when this truck still carries one sale."""
        self.ensure_one()
        sale_lines = self.cargo_ids.sale_line_id
        if self.sale_line_id:
            sale_lines |= self.sale_line_id
        if len(sale_lines) > 1:
            return self.env["sale.order"], self.env["sale.order.line"]
        sale_line = sale_lines[:1]
        sale = sale_line.order_id or self.sale_id
        return sale, sale_line

    def action_split_trip(self):
        self.ensure_one()
        sale, sale_line = self._sale_link_for_split()
        action = super().action_split_trip()
        new_trip = self.browse(action.get("res_id"))
        if new_trip and (sale or sale_line):
            new_trip.write(
                {
                    "sale_id": sale.id,
                    "sale_line_id": sale_line.id,
                }
            )
        return action

    def action_view_sales(self):
        self.ensure_one()
        sales = self.cargo_sale_order_ids
        if not sales:
            return {"type": "ir.actions.act_window_close"}
        action = self.env["ir.actions.act_window"]._for_xml_id("sale.action_orders")
        if len(sales) == 1:
            action["views"] = [(self.env.ref("sale.view_order_form").id, "form")]
            action["res_id"] = sales.id
        else:
            action["domain"] = [("id", "in", sales.ids)]
        action["context"] = {"create": False}
        action["name"] = self.env._("Sales Orders")
        return action

    def _get_passenger_count(self, vehicle):
        if not vehicle or vehicle.operation != "passenger":
            return 0
        model = vehicle.model_id
        if model.vehicle_type == "bus":
            return max(0, int((model.seats or 0) + (model.standing_capacity or 0)))
        return max(0, int(model.passenger_capacity or 0))

    def _prepare_seat_ticket_vals(self, sequence_number):
        self.ensure_one()
        return {
            "name": f"{self.name}-{sequence_number}",
            "tms_order_id": self.id,
        }

    def _sync_passenger_seat_tickets(self):
        seat_ticket = self.env["seat.ticket"]
        for order in self:
            passenger_count = order._get_passenger_count(order.vehicle_id)
            sold_tickets = order.seat_ticket_ids.filtered("sale_line_id")
            if not passenger_count:
                order.seat_ticket_ids.filtered(lambda t: not t.sale_line_id).unlink()
                continue
            order.seat_ticket_ids.filtered(lambda t: not t.sale_line_id).unlink()
            tickets_to_create = passenger_count - len(sold_tickets)
            if tickets_to_create <= 0:
                continue
            start_index = len(order.seat_ticket_ids)
            seat_ticket.create(
                [
                    order._prepare_seat_ticket_vals(start_index + offset + 1)
                    for offset in range(tickets_to_create)
                ]
            )

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        orders.filtered("vehicle_id")._sync_passenger_seat_tickets()
        return orders

    def write(self, vals):
        if "seat_ticket_ids" in vals:
            tickets = vals.get("seat_ticket_ids", [])
            for command in tickets:
                if command[0] == 2:
                    self.env["seat.ticket"].browse(command[1]).unlink()

        result = super().write(vals)

        if "vehicle_id" in vals:
            self._sync_passenger_seat_tickets()

        if "stage_id" in vals:
            stage = self.env.ref("tms.tms_stage_order_completed")
            if vals["stage_id"] == stage.id:
                for order in self:
                    for line in order.sale_id.order_line:
                        template = line.product_id.product_tmpl_id
                        if template.transport_type == "cargo":
                            continue
                        line.qty_delivered = line.product_uom_qty
                    weight_lines = order.cargo_ids.sale_line_id
                    if (
                        order.sale_line_id.product_id.product_tmpl_id.transport_type
                        == "cargo"
                    ):
                        weight_lines |= order.sale_line_id
                    for line in weight_lines:
                        trips = line.tms_order_ids | line.cargo_ids.order_id
                        if trips and all(trip.stage_id == stage for trip in trips):
                            line.qty_delivered = line.product_uom_qty

        return result
