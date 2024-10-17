from odoo import api, fields, models


class SaleOrderLineTrip(models.TransientModel):
    _name = "sale.order.line.trip"
    order_line_id = fields.Many2one("sale.order.line")

    has_route = fields.Boolean(string="Use Routes")
    route = fields.Many2one("tms.route")
    origin = fields.Many2one(
        "res.partner",
        domain="[('tms_location', '=', 'True')]",
        context={"default_tms_location": True},
    )
    destination = fields.Many2one(
        "res.partner",
        domain="[('tms_location', '=', 'True')]",
        context={"default_tms_location": True},
    )
    start = fields.Datetime(string="Scheduled start")
    end = fields.Datetime(string="Scheduled end")

    order_confirmed = fields.Boolean(readonly=True)

    @api.onchange("origin", "destination", "start", "end", "has_route", "route")
    def _compute_readonly_fields(self):
        state = self.order_line_id.order_id.state
        if state == "sale" or state == "cancelled":
            self.order_confirmed = True
        else:
            self.order_confirmed = False
