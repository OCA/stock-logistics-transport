# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.tms_product.models.product_template import BOOKING_TYPES


class TmsRateCard(models.Model):
    _name = "tms.rate.card"
    _description = "Transport Rate Card"
    _order = "partner_id, id"

    @api.model
    def _selection_transit_mode(self):
        return self.env["product.template"]._selection_transit_mode()

    name = fields.Char(required=True, index=True)
    partner_id = fields.Many2one(
        "res.partner",
        string="Customer",
        help="Empty applies to every customer.",
    )
    transport_type = fields.Selection(
        [("cargo", "Cargo"), ("passenger", "Passenger")],
        required=True,
        default="cargo",
    )
    transit_mode = fields.Selection(
        selection="_selection_transit_mode",
        required=True,
    )
    booking_type = fields.Selection(BOOKING_TYPES, required=True)
    currency_id = fields.Many2one(
        "res.currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    category_id = fields.Many2one(
        "res.partner.category",
        string="Tag",
        help="Applies to customers with this tag when they have no private card.",
    )
    date_start = fields.Date(string="Valid from")
    date_end = fields.Date(string="Valid until")
    line_ids = fields.One2many("tms.rate.card.line", "rate_card_id")

    @api.constrains("date_start", "date_end")
    def _check_validity_window(self):
        for card in self:
            if card.date_start and card.date_end and card.date_end < card.date_start:
                raise ValidationError(
                    self.env._("The end date must be on or after the start date.")
                )

    _name_uniq = models.Constraint(
        "unique(name)",
        "The rate code must be unique.",
    )

    @api.model
    def _unit_price(
        self,
        partner,
        transport_type,
        transit_mode,
        booking_type,
        origin,
        destination,
        quantity,
        currency,
        company,
        on_date,
        exchange_date=None,
    ):
        """Unit price for this customer, mode, lane, and quantity."""
        if (
            not transport_type
            or not transit_mode
            or not booking_type
            or not origin
            or not destination
        ):
            return None
        day = fields.Date.to_date(on_date) or fields.Date.context_today(self)
        domain = [
            ("transport_type", "=", transport_type),
            ("transit_mode", "=", transit_mode),
            ("booking_type", "=", booking_type),
            ("company_id", "in", [False, company.id] if company else [False]),
        ]
        cards = self.sudo().search(domain).filtered(lambda card: card._covers(day))
        groups = []
        if partner:
            groups.append(cards.filtered(lambda card: card.partner_id == partner))
            commercial = partner.commercial_partner_id
            if commercial and commercial != partner:
                groups.append(
                    cards.filtered(lambda card: card.partner_id == commercial)
                )
        tags = self._partner_tags(partner)
        if tags:
            groups.append(
                cards.filtered(
                    lambda card: not card.partner_id and card.category_id in tags
                )
            )
        groups.append(
            cards.filtered(lambda card: not card.partner_id and not card.category_id)
        )
        fx_day = fields.Date.to_date(exchange_date) or day
        for card in [card for group in groups for card in group]:
            quote = card._lane_quote(
                origin, destination, quantity, currency, company, fx_day
            )
            if quote is not None:
                return quote
        return None

    @api.model
    def _partner_tags(self, partner):
        if not partner:
            return self.env["res.partner.category"]
        return (partner | partner.commercial_partner_id).category_id

    @api.model
    def _sync_demo_tag(self):
        """Keep the demo VIP card and customer on the VIP Clients tag."""
        tag = self.env.ref(
            "tms_sale.demo_partner_category_vip", raise_if_not_found=False
        )
        card = self.env.ref(
            "tms_sale.demo_rate_card_road_ftl_vip", raise_if_not_found=False
        )
        partner = self.env.ref(
            "tms_sale.demo_tms_sale_customer", raise_if_not_found=False
        )
        if tag and card and card.category_id != tag:
            card.category_id = tag
        if tag and partner and tag not in partner.category_id:
            partner.write({"category_id": [(4, tag.id)]})

    def _covers(self, day):
        """True when this card is valid on the sale date."""
        self.ensure_one()
        if self.date_start and self.date_start > day:
            return False
        if self.date_end and self.date_end < day:
            return False
        return True

    def _lane_quote(self, origin, destination, quantity, currency, company, on_date):
        """Base price, converted price, and the rate applied on on_date."""
        self.ensure_one()
        if not origin or not destination:
            return None
        lane = self.line_ids.filtered(
            lambda line: line.origin_id == origin
            and line.destination_id == destination
        )[:1]
        if not lane:
            return None
        base = lane._unit_price(quantity)
        if base is None:
            return None
        day = fields.Date.to_date(on_date) or fields.Date.context_today(self)
        converted, rate = self._convert_amount(base, currency, company, day)
        return {
            "price": converted,
            "base": base,
            "currency": self.currency_id,
            "rate": rate,
            "date": day,
        }

    def _convert_amount(self, amount, currency, company, day):
        """Return (amount in the sale currency, rate from the card currency)."""
        self.ensure_one()
        company = company or self.env.company
        if not currency or currency == self.currency_id:
            return amount, 1.0
        converted = self.currency_id._convert(amount, currency, company, day)
        rate = converted / amount if amount else 0.0
        return converted, rate
