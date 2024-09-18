from odoo import api, fields, models


class SeatTicketLine(models.TransientModel):
    _name = "seat.ticket.line"

    order_line_id = fields.Many2one("sale.order.line")
    trip_id = fields.Many2one("tms.order", options={"no_create": True})
    ticket_ids = fields.Many2many(
        "seat.ticket",
        options={"no_create": True},
    )
    order_confirmed = fields.Boolean(readonly=True)

    @api.onchange("trip_id")
    def _compute_readonly_fields(self):
        state = self.order_line_id.order_id.state
        if state == "sale" or state == "cancelled":
            self.order_confirmed = True
        else:
            self.order_confirmed = False
