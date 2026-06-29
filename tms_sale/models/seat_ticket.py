# Copyright (C) 2024 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SeatTicket(models.Model):
    _name = "seat.ticket"
    _description = "Seat Ticket"

    name = fields.Char(
        copy=False,
        readonly=False,
        index="trigram",
        default=lambda self: self.env._("New ticket"),
    )
    tms_order_id = fields.Many2one("tms.order", store=True)
    product_id = fields.Many2one(
        "product.product",
        string="Seat Service",
        domain=(
            "[('type', '=', 'service'), ('product_tmpl_id.tms_trip', '=', True), "
            "('product_tmpl_id.trip_product_type', '=', 'seat')]"
        ),
    )
    sale_line_id = fields.Many2one("sale.order.line")
    sale_order_id = fields.Many2one("sale.order", related="sale_line_id.order_id")
    customer_id = fields.Many2one(
        "res.partner", related="sale_line_id.order_id.partner_id"
    )
    price = fields.Float()
    available = fields.Selection(
        [("available", "Available"), ("not_available", "Not available")],
        default="available",
        readonly=True,
    )

    @api.model
    def write(self, vals):
        res = super().write(vals)
        for record in self:
            if "sale_line_id" in vals:
                if vals.get("sale_line_id"):
                    record.available = "not_available"
                else:
                    record.available = "available"
        return res

    @api.model
    def _prepare_vals_from_trip(self, vals):
        trip = self.env["tms.order"].browse(vals.get("tms_order_id"))
        if not trip:
            return vals
        product = trip.vehicle_id.tms_service_product_id
        if product and not vals.get("product_id"):
            vals["product_id"] = product.id
        if product and not vals.get("price"):
            vals["price"] = product.lst_price
        new_ticket_label = self.env._("New ticket")
        if not vals.get("name") or vals.get("name") == new_ticket_label:
            vals["name"] = f"{trip.name}-{len(trip.seat_ticket_ids) + 1}"
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        return super().create(
            [self._prepare_vals_from_trip(dict(vals)) for vals in vals_list]
        )
