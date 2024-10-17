# Copyright (C) 2024 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class SeatTicket(models.Model):
    _name = "seat.ticket"

    name = fields.Char(
        copy=False,
        readonly=False,
        index="trigram",
        default=lambda self: _("New ticket"),
    )
    tms_order_id = fields.Many2one("tms.order", store=True)
    sale_line_id = fields.Many2one("sale.order.line")

    @api.model
    def create(self, vals):
        if vals.get("name", _("New")) == _("New ticket"):
            trip = self.env["tms.order"].browse(vals["tms_order_id"])
            vals["name"] = f"{trip.name}-{len(trip.seat_ticket_ids) + 1}"

        return super().create(vals)
