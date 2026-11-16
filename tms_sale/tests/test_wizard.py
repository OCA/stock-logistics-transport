# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta
from unittest.mock import patch

from odoo.addons.base.tests.common import BaseCommon


class TestTmsSaleWizard(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        cls.partner = cls.env["res.partner"].create({"name": "Wizard Customer"})
        cls.origin = cls.env["res.partner"].create(
            {"name": "Origin", "tms_location": True}
        )
        cls.destination = cls.env["res.partner"].create(
            {"name": "Destination", "tms_location": True}
        )
        cls.trip_template = cls.env["product.template"].create(
            {"name": "Trip", "type": "service", "list_price": 50.0}
        )
        cls.trip_template.write(
            {
                "transport_type": "cargo",
                "transit_mode": "road",
                "booking_type": "full_asset",
            }
        )
        cls.start = datetime.now()
        cls.end = cls.start + timedelta(hours=1)

    def _create_trip_line(self, state="draft"):
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        if state == "sale":
            order = order.with_context(default_state="sale")
        line = self.env["sale.order.line"].create(
            {
                "order_id": order.id,
                "product_id": self.trip_template.product_variant_ids.id,
                "product_uom_qty": 1,
                "tms_origin_id": self.origin.id,
                "tms_destination_id": self.destination.id,
                "tms_scheduled_date_start": self.start,
                "tms_scheduled_date_end": self.end,
            }
        )
        if state == "sale":
            order.action_confirm()
        elif state == "cancel":
            order.action_cancel()
        return line

    def test_trip_wizard_defaults_the_order_rate_card(self):
        line = self._create_trip_line()
        card = self.env["tms.rate.card"].create(
            {
                "name": "WIZARD-ROAD",
                "transport_type": "cargo",
                "transit_mode": "road",
                "booking_type": "full_asset",
            }
        )
        line.order_id.rate_card_id = card
        wizard = (
            self.env["sale.order.line.trip"]
            .with_context(default_order_line_id=line.id)
            .create({})
        )
        self.assertEqual(wizard.rate_card_id, card)

    def test_trip_wizard_editable_on_draft_order(self):
        line = self._create_trip_line()
        wizard = self.env["sale.order.line.trip"].new({"order_line_id": line.id})
        wizard._compute_readonly_fields()
        self.assertFalse(wizard.order_confirmed)

    def test_trip_wizard_readonly_on_confirmed_order(self):
        line = self._create_trip_line(state="sale")
        wizard = self.env["sale.order.line.trip"].new({"order_line_id": line.id})
        wizard._compute_readonly_fields()
        self.assertTrue(wizard.order_confirmed)

    def test_trip_wizard_readonly_on_cancelled_order(self):
        line = self._create_trip_line(state="cancel")
        wizard = self.env["sale.order.line.trip"].new({"order_line_id": line.id})
        wizard._compute_readonly_fields()
        self.assertTrue(wizard.order_confirmed)

    def test_seat_ticket_wizard_editable_on_draft_order(self):
        line = self._create_trip_line()
        tms_order = self.env["tms.order"].create(
            {
                "name": "TRIP-WIZ",
                "company_id": self.env.company.id,
                "origin_id": self.origin.id,
                "destination_id": self.destination.id,
            }
        )
        wizard = self.env["seat.ticket.line"].new(
            {"order_line_id": line.id, "trip_id": tms_order.id}
        )
        wizard._compute_readonly_fields()
        self.assertFalse(wizard.order_confirmed)

    def test_seat_ticket_wizard_readonly_on_confirmed_order(self):
        line = self._create_trip_line(state="sale")
        tms_order = self.env["tms.order"].create(
            {
                "name": "TRIP-WIZ-2",
                "company_id": self.env.company.id,
                "origin_id": self.origin.id,
                "destination_id": self.destination.id,
            }
        )
        wizard = self.env["seat.ticket.line"].new(
            {"order_line_id": line.id, "trip_id": tms_order.id}
        )
        wizard._compute_readonly_fields()
        self.assertTrue(wizard.order_confirmed)

    def test_provider_distance_from_origin_and_destination(self):
        def fake_apply(wizard):
            wizard.distance = 42.5
            wizard.distance_uom = "km"
            return True

        line = self._create_trip_line()
        wizard = self.env["sale.order.line.trip"].new(
            {
                "order_line_id": line.id,
                "origin": self.origin.id,
                "destination": self.destination.id,
            }
        )
        route_model = type(self.env["tms.route"])
        with (
            patch.object(route_model, "_routing_provider_ready", lambda model: True),
            patch.object(type(wizard), "_apply_provider_distance", fake_apply),
        ):
            wizard._onchange_distance()
        self.assertEqual(wizard.distance, 42.5)
        self.assertEqual(wizard.distance_uom, "km")

    def test_wizard_reloads_container_lines(self):
        self.trip_template.write(
            {"transit_mode": "water", "booking_type": "full_asset"}
        )
        line = self._create_trip_line()
        self.env["tms.cargo"].create(
            {
                "sale_line_id": line.id,
                "container_type": "20dry",
                "container_number": "TCLU0000001",
                "quantity": 1,
            }
        )
        wizard = (
            self.env["sale.order.line.trip"]
            .with_context(default_order_line_id=line.id)
            .create({})
        )
        self.assertEqual(wizard.shipment_unit, "container")
        self.assertEqual(wizard.cargo_line_ids.container_number, "TCLU0000001")
        self.assertEqual(wizard.cargo_line_ids.container_type, "20dry")
