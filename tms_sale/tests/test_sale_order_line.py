# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta
from unittest.mock import PropertyMock, patch

from odoo.exceptions import ValidationError

from odoo.addons.base.tests.common import BaseCommon


class TestSaleOrderLineTms(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        cls.partner = cls.env["res.partner"].create({"name": "Test Customer"})
        cls.origin = cls.env["res.partner"].create(
            {"name": "Origin", "tms_location": True}
        )
        cls.destination = cls.env["res.partner"].create(
            {"name": "Destination", "tms_location": True}
        )
        cls.start = datetime.now()
        cls.end = cls.start + timedelta(hours=2)
        cls.trip_template = cls.env["product.template"].create(
            {"name": "Trip Service", "type": "service", "list_price": 100.0}
        )
        cls.trip_template.write(
            {
                "transport_type": "cargo",
                "transit_mode": "road",
                "booking_type": "full_asset",
            }
        )
        cls.trip_product = cls.trip_template.product_variant_ids[0]

    def _create_line(self, **extra):
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        vals = {
            "order_id": order.id,
            "product_id": self.trip_product.id,
            "product_uom_qty": 1,
            "tms_origin_id": self.origin.id,
            "tms_destination_id": self.destination.id,
            "tms_scheduled_date_start": self.start,
            "tms_scheduled_date_end": self.end,
        }
        vals.update(extra)
        return self.env["sale.order.line"].create(vals)

    def _link_trip_wizard(self, line):
        self.env["sale.order.line.trip"].create({"order_line_id": line.id})
        line.invalidate_recordset(["trip_line_ids"])

    def test_compute_clears_fields_without_product(self):
        line = self.env["sale.order.line"].new(
            {"order_id": self.env["sale.order"].new()}
        )
        line._compute_sale_order_line_tms()
        self.assertFalse(line.has_trip_product)
        self.assertFalse(line.seat_ticket)

    def test_cargo_service_sets_trip_product(self):
        weight_template = self.env["product.template"].create(
            {"name": "Weight Trip", "type": "service", "list_price": 80.0}
        )
        weight_template.write(
            {
                "transport_type": "cargo",
                "transit_mode": "road",
                "booking_type": "shared_space",
            }
        )
        line = self.env["sale.order.line"].create(
            {
                "order_id": self.env["sale.order"]
                .create({"partner_id": self.partner.id})
                .id,
                "product_id": weight_template.product_variant_ids.id,
                "product_uom_qty": 1,
            }
        )
        line._compute_sale_order_line_tms()
        self.assertTrue(line.has_trip_product)

    def test_compute_route_distance_factor(self):
        route = self.env["tms.route"].create(
            {
                "name": "Main Route",
                "origin_location_id": self.origin.id,
                "destination_location_id": self.destination.id,
                "distance": 42.0,
                "estimated_time": 1.0,
                "distance_uom": self.env.ref("uom.product_uom_km").id,
                "estimated_time_uom": self.env.ref("uom.product_uom_hour").id,
            }
        )
        line = self._create_line(tms_route_id=route.id, tms_route_flag=True)
        self.assertIn("Distance: 42.00", line.name)

    def test_prepare_tms_values_int_duration(self):
        line = self._create_line()
        with (
            patch.object(
                type(line),
                "tms_scheduled_date_end",
                new_callable=PropertyMock,
                return_value=7200,
            ),
            patch.object(
                type(line),
                "tms_scheduled_date_start",
                new_callable=PropertyMock,
                return_value=0,
            ),
        ):
            vals = line._prepare_tms_values(so_id=line.order_id.id, sol_id=line.id)
        self.assertEqual(vals["scheduled_duration"], 2.0)

    def test_update_tickets(self):
        line = self._create_line()
        self.assertTrue(line._update_tickets(self.env["seat.ticket"]))

    def test_constraint_route_required(self):
        line = self._create_line(tms_route_flag=True)
        self._link_trip_wizard(line)
        with self.assertRaises(ValidationError):
            line.write({"tms_route_id": False})

    def test_constraint_origin_required(self):
        line = self._create_line(tms_origin_id=False)
        self._link_trip_wizard(line)
        with self.assertRaises(ValidationError):
            line.write({"tms_origin_id": False})

    def test_constraint_destination_required(self):
        line = self._create_line(tms_destination_id=False)
        self._link_trip_wizard(line)
        with self.assertRaises(ValidationError):
            line.write({"tms_destination_id": False})

    def test_constraint_start_date_required(self):
        line = self._create_line(tms_scheduled_date_start=False)
        self._link_trip_wizard(line)
        with self.assertRaises(ValidationError):
            line.write({"tms_scheduled_date_start": False})

    def test_constraint_end_date_required(self):
        line = self._create_line(tms_scheduled_date_end=False)
        self._link_trip_wizard(line)
        with self.assertRaises(ValidationError):
            line.write({"tms_scheduled_date_end": False})

    def test_constraint_seat_requires_ticket(self):
        seat_template = self.env["product.template"].create(
            {"name": "Seat", "type": "service", "list_price": 25.0}
        )
        seat_template.write(
            {
                "transport_type": "passenger",
                "transit_mode": "road",
                "booking_type": "shared_space",
            }
        )
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        line = self.env["sale.order.line"].create(
            {
                "order_id": order.id,
                "product_id": seat_template.product_variant_ids.id,
                "product_uom_qty": 1,
                "tms_origin_id": self.origin.id,
                "tms_destination_id": self.destination.id,
            }
        )
        self.env.cr.execute(
            "UPDATE sale_order SET state = 'sale' WHERE id = %s", [order.id]
        )
        order.invalidate_recordset(["state"])
        with self.assertRaises(ValidationError):
            line._check_required_fields()
