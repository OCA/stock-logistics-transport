# Copyright (C) 2019 Brian McMaster
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class TMSOrder(models.Model):
    _inherit = "tms.order"

    sale_id = fields.Many2one("sale.order", copy=False)
    sale_line_id = fields.Many2one("sale.order.line", copy=False)
    seat_ticket_ids = fields.One2many("seat.ticket", "tms_order_id")
    vehicle_operation = fields.Selection(related="vehicle_id.operation")
    seat_sale_order_ids = fields.Many2many(
        "sale.order",
        compute="_compute_seat_sale_orders",
    )
    seat_sale_order_count = fields.Integer(
        compute="_compute_seat_sale_orders",
        string="Sales Orders",
    )

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

    def action_view_sales(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "views": [[False, "form"]],
            "res_id": self.sale_line_id.order_id.id or self.sale_id.id,
            "context": {"create": False},
            "name": self.env._("Sales Orders"),
        }

    def _get_passenger_count(self, vehicle):
        if not vehicle or vehicle.operation != "passenger":
            return 0
        return max(0, int(vehicle.capacity))

    def _prepare_seat_ticket_vals(self, sequence_number):
        self.ensure_one()
        vals = {
            "name": f"{self.name}-{sequence_number}",
            "tms_order_id": self.id,
        }
        product = self.vehicle_id.tms_service_product_id
        if product:
            vals["product_id"] = product.id
            vals["price"] = product.lst_price
        return vals

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
                        line.qty_delivered = line.product_uom_qty

        return result
