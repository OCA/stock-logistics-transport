# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models

RATE_TYPES = [
    ("flat", "Flat"),
    ("bracket", "Bracket"),
]


class TmsRateCardLine(models.Model):
    _name = "tms.rate.card.line"
    _description = "Transport Rate Lane"

    rate_card_id = fields.Many2one(
        "tms.rate.card",
        required=True,
        ondelete="cascade",
    )
    currency_id = fields.Many2one(related="rate_card_id.currency_id")
    origin_id = fields.Many2one(
        "res.partner",
        string="Origin",
        required=True,
        domain="[('tms_location', '=', True)]",
        context={"default_tms_location": True},
    )
    destination_id = fields.Many2one(
        "res.partner",
        string="Destination",
        required=True,
        domain="[('tms_location', '=', True)]",
        context={"default_tms_location": True},
    )
    rate_type = fields.Selection(RATE_TYPES, required=True, default="flat")
    fixed_price = fields.Monetary(currency_field="currency_id")
    bracket_ids = fields.One2many("tms.rate.bracket", "rate_line_id")

    def _unit_price(self, quantity):
        """Flat amount, or the bracket that contains this quantity."""
        self.ensure_one()
        if self.rate_type == "flat":
            return self.fixed_price
        matches = self.bracket_ids.filtered(
            lambda bracket: bracket.weight_or_qty_min
            <= quantity
            <= bracket.weight_or_qty_max
        )
        if not matches:
            return None
        bracket = matches.sorted(
            key=lambda item: (
                item.weight_or_qty_max - item.weight_or_qty_min,
                item.weight_or_qty_min,
                item.id,
            )
        )[:1]
        return bracket.price_per_unit
