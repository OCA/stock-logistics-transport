# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class TmsRateBracket(models.Model):
    _name = "tms.rate.bracket"
    _description = "Transport Rate Bracket"
    _order = "weight_or_qty_min, id"

    rate_line_id = fields.Many2one(
        "tms.rate.card.line",
        required=True,
        ondelete="cascade",
    )
    currency_id = fields.Many2one(related="rate_line_id.currency_id")
    weight_or_qty_min = fields.Float(string="Minimum", required=True)
    weight_or_qty_max = fields.Float(string="Maximum", required=True)
    price_per_unit = fields.Monetary(currency_field="currency_id", required=True)

    @api.constrains("weight_or_qty_min", "weight_or_qty_max", "rate_line_id")
    def _check_range(self):
        for bracket in self:
            if bracket.weight_or_qty_max < bracket.weight_or_qty_min:
                raise ValidationError(
                    self.env._("The maximum must be at least the minimum.")
                )
            others = bracket.rate_line_id.bracket_ids - bracket
            overlap = others.filtered(
                lambda other, item=bracket: item.weight_or_qty_min
                <= other.weight_or_qty_max
                and other.weight_or_qty_min <= item.weight_or_qty_max
            )
            if overlap:
                raise ValidationError(
                    self.env._("Brackets on the same lane must not overlap.")
                )
