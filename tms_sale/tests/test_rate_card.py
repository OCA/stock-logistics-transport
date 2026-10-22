# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import timedelta

from psycopg2 import IntegrityError

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tools import mute_logger

from odoo.addons.base.tests.common import BaseCommon


class TestTmsRateCard(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.origin = cls.env["res.partner"].create(
            {"name": "Rate Origin", "tms_location": True}
        )
        cls.destination = cls.env["res.partner"].create(
            {"name": "Rate Destination", "tms_location": True}
        )
        cls.other_destination = cls.env["res.partner"].create(
            {"name": "Other Destination", "tms_location": True}
        )
        cls.customer = cls.env["res.partner"].create({"name": "Rated Customer"})
        cls.other = cls.env["res.partner"].create({"name": "Other Customer"})
        cls.commercial = cls.env["res.partner"].create(
            {"name": "Rated Company", "is_company": True}
        )
        cls.contact = cls.env["res.partner"].create(
            {"name": "Rated Buyer", "parent_id": cls.commercial.id}
        )
        cls.ftl = cls._service(cls, "FTL Rate", 100.0, cargo_mode="ftl")
        cls.ltl = cls._service(cls, "LTL Rate", 100.0, cargo_mode="ltl")
        cls.fcl = cls._service(cls, "FCL Rate", 100.0, cargo_mode="fcl")
        cls.seat = cls._service(
            cls,
            "Seat Rate",
            25.0,
            transport_type="passenger",
            transit_mode="road",
            booking_type="shared_space",
        )

    def _service(
        self,
        name,
        price,
        cargo_mode=None,
        transport_type="cargo",
        transit_mode=None,
        booking_type=None,
    ):
        implied = {
            "ftl": ("road", "full_asset"),
            "ltl": ("road", "shared_space"),
            "fcl": ("water", "full_asset"),
        }
        if cargo_mode:
            transit_mode, booking_type = implied[cargo_mode]
        template = self.env["product.template"].create(
            {"name": name, "type": "service", "list_price": price}
        )
        template.write(
            {
                "transport_type": transport_type,
                "taxes_id": [(5, 0, 0)],
                "transit_mode": transit_mode,
                "booking_type": booking_type,
            }
        )
        return template

    def _card(self, name, transit_mode, booking_type, partner=None, currency=None):
        values = {
            "name": name,
            "transit_mode": transit_mode,
            "booking_type": booking_type,
        }
        if partner:
            values["partner_id"] = partner.id
        if currency:
            values["currency_id"] = currency.id
        return self.env["tms.rate.card"].create(values)

    def _flat(self, card, price, origin=None, destination=None):
        return self.env["tms.rate.card.line"].create(
            {
                "rate_card_id": card.id,
                "origin_id": (origin or self.origin).id,
                "destination_id": (destination or self.destination).id,
                "rate_type": "flat",
                "fixed_price": price,
            }
        )

    def _sale_line(self, product, partner, quantity=1.0, destination=None):
        order = self.env["sale.order"].create({"partner_id": partner.id})
        return self.env["sale.order.line"].create(
            {
                "order_id": order.id,
                "product_id": product.product_variant_ids.id,
                "product_uom_qty": quantity,
                "tms_origin_id": self.origin.id,
                "tms_destination_id": (destination or self.destination).id,
            }
        )

    def test_service_keeps_network_and_booking(self):
        self.assertEqual(self.ftl.transit_mode, "road")
        self.assertEqual(self.ftl.booking_type, "full_asset")
        self.assertEqual(self.fcl.transit_mode, "water")
        self.assertEqual(self.seat.booking_type, "shared_space")

    def test_origin_and_destination_update_the_unit_price(self):
        card = self._card("ROAD-FTL-LATER", "road", "full_asset")
        self._flat(card, 250.0)
        order = self.env["sale.order"].create({"partner_id": self.customer.id})
        line = self.env["sale.order.line"].create(
            {
                "order_id": order.id,
                "product_id": self.ftl.product_variant_ids.id,
                "product_uom_qty": 1,
            }
        )
        self.assertEqual(line.price_unit, 100.0)
        line.write(
            {
                "tms_origin_id": self.origin.id,
                "tms_destination_id": self.destination.id,
            }
        )
        self.assertEqual(line.price_unit, 250.0)

    def test_selected_rate_card_sets_the_unit_price(self):
        public = self._card("ROAD-FTL-PICK-PUBLIC", "road", "full_asset")
        self._flat(public, 250.0)
        private = self._card(
            "ROAD-FTL-PICK-CUSTOMER", "road", "full_asset", partner=self.customer
        )
        self._flat(private, 80.0)
        order = self.env["sale.order"].create(
            {"partner_id": self.customer.id, "rate_card_id": public.id}
        )
        line = self.env["sale.order.line"].create(
            {
                "order_id": order.id,
                "product_id": self.ftl.product_variant_ids.id,
                "product_uom_qty": 1,
                "tms_origin_id": self.origin.id,
                "tms_destination_id": self.destination.id,
            }
        )
        self.assertEqual(line.price_unit, 250.0)
        line.rate_card_id = private
        self.assertEqual(line.price_unit, 80.0)

    def test_missing_network_does_not_use_a_card(self):
        self.ftl.transit_mode = False
        card = self._card("ROAD-FTL-IMPLIED", "road", "full_asset")
        self._flat(card, 250.0)
        line = self._sale_line(self.ftl, self.customer)
        self.assertEqual(line.price_unit, 100.0)

    def test_public_flat_replaces_the_list_price(self):
        card = self._card("ROAD-FTL-PUBLIC", "road", "full_asset")
        self._flat(card, 250.0)
        line = self._sale_line(self.ftl, self.other)
        self.assertEqual(line.price_unit, 250.0)

    def test_customer_card_beats_the_public_card(self):
        public = self._card("ROAD-FTL-PUBLIC", "road", "full_asset")
        self._flat(public, 250.0)
        private = self._card(
            "ROAD-FTL-CUSTOMER", "road", "full_asset", partner=self.customer
        )
        self._flat(private, 80.0)
        self.assertEqual(self._sale_line(self.ftl, self.customer).price_unit, 80.0)
        self.assertEqual(self._sale_line(self.ftl, self.other).price_unit, 250.0)

    def test_commercial_partner_is_used_when_the_contact_has_no_card(self):
        public = self._card("ROAD-FTL-PUBLIC", "road", "full_asset")
        self._flat(public, 250.0)
        company = self._card(
            "ROAD-FTL-COMPANY", "road", "full_asset", partner=self.commercial
        )
        self._flat(company, 90.0)
        line = self._sale_line(self.ftl, self.contact)
        self.assertEqual(line.price_unit, 90.0)

    def test_zero_flat_price_is_applied(self):
        card = self._card("ROAD-FTL-FREE", "road", "full_asset")
        self._flat(card, 0.0)
        line = self._sale_line(self.ftl, self.customer)
        self.assertEqual(line.price_unit, 0.0)
        self.assertFalse(line.spot_quote)

    def test_bracket_uses_the_range_that_contains_the_quantity(self):
        card = self._card("ROAD-LTL-QTY", "road", "shared_space")
        lane = self.env["tms.rate.card.line"].create(
            {
                "rate_card_id": card.id,
                "origin_id": self.origin.id,
                "destination_id": self.destination.id,
                "rate_type": "bracket",
            }
        )
        self.env["tms.rate.bracket"].create(
            {
                "rate_line_id": lane.id,
                "weight_or_qty_min": 0,
                "weight_or_qty_max": 10,
                "price_per_unit": 5.0,
            }
        )
        self.assertEqual(self._sale_line(self.ltl, self.customer, 4).price_unit, 5.0)
        missed = self._sale_line(self.ltl, self.customer, 11)
        self.assertEqual(missed.price_unit, 0.0)
        self.assertTrue(missed.spot_quote)

    def test_ocean_full_asset_uses_the_water_card(self):
        self.assertEqual(
            self._sale_line(self.fcl, self.customer)._tms_booking_type(),
            "full_asset",
        )
        road = self._card("ROAD-FULL-SKIP", "road", "full_asset")
        self._flat(road, 250.0)
        card = self._card("WATER-FULL", "water", "full_asset")
        self._flat(card, 400.0)
        line = self._sale_line(self.fcl, self.customer)
        self.assertEqual(line.price_unit, 400.0)

    def test_missing_lane_asks_for_a_spot_quote(self):
        card = self._card("ROAD-FTL-OTHER", "road", "full_asset")
        self._flat(card, 250.0, destination=self.other_destination)
        line = self._sale_line(self.ftl, self.customer)
        self.assertEqual(line.price_unit, 0.0)
        self.assertTrue(line.spot_quote)
        self.assertTrue(line.order_id.spot_quote_required)

    def test_customer_tag_beats_the_public_card(self):
        public = self._card("ROAD-FTL-PUBLIC-TAG", "road", "full_asset")
        self._flat(public, 250.0)
        tag = self.env["res.partner.category"].create({"name": "VIP Clients Test"})
        tag_card = self.env["tms.rate.card"].create(
            {
                "name": "ROAD-FTL-TAG",
                "transit_mode": "road",
                "booking_type": "full_asset",
                "category_id": tag.id,
            }
        )
        self._flat(tag_card, 160.0)
        self.customer.category_id = tag
        self.assertEqual(self._sale_line(self.ftl, self.customer).price_unit, 160.0)
        self.assertEqual(self._sale_line(self.ftl, self.other).price_unit, 250.0)

    def test_private_card_beats_the_customer_tag(self):
        tag = self.env["res.partner.category"].create({"name": "Wholesale Test"})
        tag_card = self.env["tms.rate.card"].create(
            {
                "name": "ROAD-FTL-WHOLESALE",
                "transit_mode": "road",
                "booking_type": "full_asset",
                "category_id": tag.id,
            }
        )
        self._flat(tag_card, 160.0)
        private = self._card(
            "ROAD-FTL-PRIVATE-TAG", "road", "full_asset", partner=self.customer
        )
        self._flat(private, 80.0)
        self.customer.category_id = tag
        line = self._sale_line(self.ftl, self.customer)
        self.assertEqual(line.price_unit, 80.0)

    def test_expired_card_is_skipped(self):
        expired = self._card(
            "ROAD-FTL-OLD", "road", "full_asset", partner=self.customer
        )
        expired.date_end = "2020-01-01"
        self._flat(expired, 80.0)
        public = self._card("ROAD-FTL-CURRENT", "road", "full_asset")
        self._flat(public, 250.0)
        line = self._sale_line(self.ftl, self.customer)
        self.assertEqual(line.price_unit, 250.0)

    def test_card_is_ignored_before_its_start_date(self):
        future = self._card("ROAD-FTL-FUTURE", "road", "full_asset")
        future.date_start = "2099-01-01"
        self._flat(future, 250.0)
        line = self._sale_line(self.ftl, self.customer)
        self.assertTrue(line.spot_quote)
        self.assertEqual(line.price_unit, 0.0)

    def test_manual_price_stays_when_the_lane_changes(self):
        card = self._card("ROAD-FTL-MANUAL", "road", "full_asset")
        self._flat(card, 250.0)
        self._flat(card, 999.0, destination=self.other_destination)
        line = self._sale_line(self.ftl, self.customer)
        line.write(
            {"price_unit": 0.0, "technical_price_unit": line.technical_price_unit}
        )
        line.tms_destination_id = self.other_destination
        self.assertEqual(line.price_unit, 0.0)

    def test_currency_is_converted_into_the_sale_currency(self):
        company = self.env.company
        foreign = self.env.ref("base.EUR")
        if foreign == company.currency_id:
            foreign = self.env.ref("base.MXN")
        today = fields.Date.context_today(self.env.user)
        rate = self.env["res.currency.rate"].search(
            [
                ("currency_id", "=", foreign.id),
                ("company_id", "=", company.id),
                ("name", "=", today),
            ],
            limit=1,
        )
        if rate:
            rate.rate = 2.0
        else:
            self.env["res.currency.rate"].create(
                {
                    "currency_id": foreign.id,
                    "company_id": company.id,
                    "name": today,
                    "rate": 2.0,
                }
            )
        card = self._card("ROAD-FTL-FX", "road", "full_asset", currency=foreign)
        self._flat(card, 100.0)
        line = self._sale_line(self.ftl, self.customer)
        expected = foreign._convert(
            100.0,
            line.currency_id,
            company,
            line.order_id.date_order,
        )
        self.assertAlmostEqual(line.price_unit, expected)
        self.assertNotAlmostEqual(line.price_unit, 100.0)
        self.assertAlmostEqual(line.tms_rate_price, 100.0)
        self.assertEqual(line.tms_rate_currency_id, foreign)
        self.assertAlmostEqual(
            line.price_unit, line.tms_rate_price * line.tms_rate_exchange
        )

    def _currency_rate(self, currency, day, value):
        company = self.env.company
        rate = self.env["res.currency.rate"].search(
            [
                ("currency_id", "=", currency.id),
                ("company_id", "=", company.id),
                ("name", "=", day),
            ],
            limit=1,
        )
        if rate:
            rate.rate = value
        else:
            rate = self.env["res.currency.rate"].create(
                {
                    "currency_id": currency.id,
                    "company_id": company.id,
                    "name": day,
                    "rate": value,
                }
            )
        return rate

    def test_shipment_date_uses_that_days_rate(self):
        company = self.env.company
        foreign = self.env.ref("base.EUR")
        if foreign == company.currency_id:
            foreign = self.env.ref("base.MXN")
        today = fields.Date.context_today(self.env.user)
        departure = today + timedelta(days=10)
        self._currency_rate(foreign, today, 2.0)
        self._currency_rate(foreign, departure, 4.0)
        self.env["ir.config_parameter"].sudo().set_param(
            "tms_sale.rate_exchange_date", "shipment"
        )
        card = self._card("ROAD-FTL-SHIP", "road", "full_asset", currency=foreign)
        self._flat(card, 100.0)
        line = self._sale_line(self.ftl, self.customer)
        line.tms_scheduled_date_start = fields.Datetime.to_datetime(departure)
        expected = foreign._convert(100.0, line.currency_id, company, departure)
        self.assertAlmostEqual(line.price_unit, expected)
        self.assertEqual(line.tms_rate_date, departure)
        self.assertFalse(line.tms_rate_locked)

    def test_order_date_freezes_the_rate_when_confirmed(self):
        company = self.env.company
        foreign = self.env.ref("base.EUR")
        if foreign == company.currency_id:
            foreign = self.env.ref("base.MXN")
        today = fields.Date.context_today(self.env.user)
        self._currency_rate(foreign, today, 2.0)
        self.env["ir.config_parameter"].sudo().set_param(
            "tms_sale.rate_exchange_date", "order"
        )
        card = self._card("ROAD-FTL-LOCK", "road", "full_asset", currency=foreign)
        self._flat(card, 100.0)
        line = self._sale_line(self.ftl, self.customer)
        line.order_id.action_confirm()
        self.assertTrue(line.tms_rate_locked)
        self.assertEqual(line.tms_rate_date, today)
        stored = line.tms_rate_exchange
        frozen = line.price_unit
        self._currency_rate(foreign, today, 8.0)
        line.order_id.date_order = fields.Datetime.now()
        fresh = foreign._convert(100.0, line.currency_id, company, today)
        self.assertNotAlmostEqual(fresh, frozen)
        self.assertAlmostEqual(line.price_unit, frozen)
        self.assertAlmostEqual(line.price_unit, line.tms_rate_price * stored)
        invoice = line.order_id._create_invoices()
        invoice_line = invoice.invoice_line_ids.filtered(
            lambda item: line in item.sale_line_ids
        )
        self.assertAlmostEqual(invoice_line.tms_rate_price, 100.0)
        self.assertEqual(invoice_line.tms_rate_currency_id, foreign)
        self.assertEqual(invoice_line.price_unit, line.price_unit)

    def test_duplicate_code_is_rejected(self):
        self._card("ROAD-FTL-UNIQUE", "road", "full_asset")
        with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self._card("ROAD-FTL-UNIQUE", "road", "full_asset")

    def test_inverted_bracket_is_rejected(self):
        card = self._card("ROAD-LTL-RANGE", "road", "shared_space")
        lane = self._flat(card, 0.0)
        lane.rate_type = "bracket"
        with self.assertRaises(ValidationError):
            self.env["tms.rate.bracket"].create(
                {
                    "rate_line_id": lane.id,
                    "weight_or_qty_min": 20,
                    "weight_or_qty_max": 10,
                    "price_per_unit": 1.0,
                }
            )

    def test_overlapping_brackets_are_rejected(self):
        card = self._card("ROAD-LTL-OVERLAP", "road", "shared_space")
        lane = self.env["tms.rate.card.line"].create(
            {
                "rate_card_id": card.id,
                "origin_id": self.origin.id,
                "destination_id": self.destination.id,
                "rate_type": "bracket",
            }
        )
        self.env["tms.rate.bracket"].create(
            {
                "rate_line_id": lane.id,
                "weight_or_qty_min": 0,
                "weight_or_qty_max": 10,
                "price_per_unit": 5.0,
            }
        )
        with self.assertRaises(ValidationError):
            self.env["tms.rate.bracket"].create(
                {
                    "rate_line_id": lane.id,
                    "weight_or_qty_min": 5,
                    "weight_or_qty_max": 15,
                    "price_per_unit": 3.0,
                }
            )
