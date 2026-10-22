# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    transport_type = fields.Selection(
        related="product_template_id.transport_type",
        store=False,
    )
    transit_mode = fields.Selection(
        related="product_template_id.transit_mode",
        store=False,
    )
    booking_type = fields.Selection(
        related="product_template_id.booking_type",
        store=False,
    )
    origin_id = fields.Many2one(
        related="tms_origin_id",
        store=False,
    )
    destination_id = fields.Many2one(
        related="tms_destination_id",
        store=False,
    )
    trip_id = fields.Many2one(
        related="tms_trip_ticket_id",
        string="Trip",
        store=False,
    )
