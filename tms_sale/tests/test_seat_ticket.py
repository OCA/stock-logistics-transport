# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.base.tests.common import BaseCommon


class TestSeatTicket(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.origin = cls.env["res.partner"].create(
            {"name": "Origin", "tms_location": True}
        )
        cls.destination = cls.env["res.partner"].create(
            {"name": "Destination", "tms_location": True}
        )
        cls.tms_order = cls.env["tms.order"].create(
            {
                "name": "TRIP-001",
                "company_id": cls.env.company.id,
                "origin_id": cls.origin.id,
                "destination_id": cls.destination.id,
            }
        )
        cls.partner = cls.env["res.partner"].create({"name": "Passenger"})
        cls.sale_order = cls.env["sale.order"].create({"partner_id": cls.partner.id})
        cls.sale_line = cls.env["sale.order.line"].create(
            {
                "order_id": cls.sale_order.id,
                "name": "Seat line",
                "product_uom_qty": 1,
            }
        )
        cls.seat_product = cls.env.ref(
            "tms_product.product_tms_seat_service"
        ).product_variant_ids[0]
        cls.vehicle_model = cls.env["fleet.vehicle.model"].create(
            {
                "name": "Bus Model",
                "brand_id": cls.env["fleet.vehicle.model.brand"]
                .create({"name": "Bus Brand"})
                .id,
            }
        )
        cls.passenger_vehicle = cls.env["fleet.vehicle"].create(
            {
                "name": "Passenger Bus",
                "model_id": cls.vehicle_model.id,
                "operation": "passenger",
                "capacity": 2,
                "tms_service_product_id": cls.seat_product.id,
            }
        )

    def test_create_default_name(self):
        ticket = self.env["seat.ticket"].create({"tms_order_id": self.tms_order.id})
        self.assertEqual(ticket.name, "TRIP-001-1")
        self.assertEqual(ticket.available, "available")

    def test_create_second_ticket_sequence(self):
        first = self.env["seat.ticket"].create({"tms_order_id": self.tms_order.id})
        second = self.env["seat.ticket"].create({"tms_order_id": self.tms_order.id})
        self.assertEqual(first.name, "TRIP-001-1")
        self.assertEqual(second.name, "TRIP-001-2")

    def test_create_keeps_explicit_name(self):
        ticket = self.env["seat.ticket"].create(
            {"tms_order_id": self.tms_order.id, "name": "VIP-1"}
        )
        self.assertEqual(ticket.name, "VIP-1")

    def test_create_defaults_product_and_price_from_vehicle(self):
        trip = self.env["tms.order"].create(
            {
                "name": "TRIP-002",
                "company_id": self.env.company.id,
                "origin_id": self.origin.id,
                "destination_id": self.destination.id,
                "vehicle_id": self.passenger_vehicle.id,
            }
        )
        self.assertEqual(len(trip.seat_ticket_ids), 2)
        ticket = trip.seat_ticket_ids[0]
        self.assertEqual(ticket.product_id, self.seat_product)
        self.assertEqual(ticket.price, self.seat_product.lst_price)

    def test_write_sale_line_marks_unavailable(self):
        ticket = self.env["seat.ticket"].create({"tms_order_id": self.tms_order.id})
        ticket.write({"sale_line_id": self.sale_line.id})
        self.assertEqual(ticket.available, "not_available")
        self.assertEqual(ticket.sale_order_id, self.sale_order)
        self.assertEqual(ticket.customer_id, self.partner)

        ticket.write({"sale_line_id": False})
        self.assertEqual(ticket.available, "available")
