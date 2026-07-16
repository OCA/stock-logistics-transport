# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta

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
        cls.trip_template.write({"tms_trip": True, "trip_product_type": "trip"})
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
