from odoo import api, fields, models


class SeatTicketLine(models.TransientModel):
    _name = "seat.ticket.line"
    _description = "Seat Ticket Line"

    order_line_id = fields.Many2one("sale.order.line")
    trip_id = fields.Many2one("tms.order")
    ticket_ids = fields.Many2many("seat.ticket")
    order_confirmed = fields.Boolean(readonly=True)

    @api.onchange("trip_id")
    def _compute_readonly_fields(self):
        state = self.order_line_id.order_id.state
        if state == "sale" or state == "cancel":
            self.order_confirmed = True
        else:
            self.order_confirmed = False
