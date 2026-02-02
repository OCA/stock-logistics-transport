# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    is_internal_carrier = fields.Boolean(
        string="Internal Carrier",
        help="Enable to mark this carrier as an internal company carrier.",
    )
    tms_team_id = fields.Many2one(
        comodel_name="tms.team",
        string="TMS Team",
        help="Default TMS team for pickings using this carrier.",
    )
    auto_create_stops = fields.Boolean(
        string="Auto Create TMS Stops",
        help="Automatically create TMS delivery stops from stock pickings.",
    )
