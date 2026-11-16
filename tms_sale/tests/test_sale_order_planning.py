# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta

from odoo.exceptions import UserError
from odoo.addons.base.tests.common import BaseCommon


class TestSaleOrderPlanning(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.partner = cls.env["res.partner"].create({"name": "Shipper"})
        cls.origin = cls.env["res.partner"].create(
            {"name": "Origin", "tms_location": True}
        )
        cls.destination = cls.env["res.partner"].create(
            {"name": "Destination", "tms_location": True}
        )
        cls.start = datetime(2026, 10, 6, 14, 0, 0)
        cls.end = cls.start + timedelta(hours=8)
        cls.kilogram = cls.env.ref("uom.product_uom_kgm")
        cls.cubic_meter = cls.env.ref("uom.product_uom_cubic_meter")

    def _product(self, name, cargo_mode=None, transit_mode=None):
        cargo = {
            "ftl": ("cargo", "road", "full_asset"),
            "ltl": ("cargo", "road", "shared_space"),
            "fcl": ("cargo", "water", "full_asset"),
            "lcl": ("cargo", "water", "shared_space"),
            "air_consolidation": ("cargo", "air", "shared_space"),
            "back_to_back": ("cargo", "air", "shared_space"),
        }
        passenger = {
            "charter": ("passenger", "road", "full_asset"),
            "cabin": ("passenger", "air", "shared_space"),
            "seat": ("passenger", "road", "shared_space"),
        }
        kind, network, booking = cargo.get(cargo_mode) or passenger[transit_mode]
        product = self.env["product.template"].create(
            {"name": name, "type": "service", "list_price": 100.0}
        )
        product.write(
            {
                "transport_type": kind,
                "transit_mode": network,
                "booking_type": booking,
            }
        )
        return product.product_variant_ids[0]

    def _sale(self, product, qty=1.0):
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        line = self.env["sale.order.line"].create(
            {
                "order_id": order.id,
                "product_id": product.id,
                "product_uom_qty": qty,
                "tms_origin_id": self.origin.id,
                "tms_destination_id": self.destination.id,
                "tms_scheduled_date_start": self.start,
                "tms_scheduled_date_end": self.end,
            }
        )
        return order, line

    def _trip(self, transport_type="cargo", **extra):
        values = {
            "origin_id": self.origin.id,
            "destination_id": self.destination.id,
            "scheduled_date_start": self.start,
            "scheduled_date_end": self.end,
            "transport_type": transport_type,
        }
        values.update(extra)
        return self.env["tms.order"].create(values)

    def test_ftl_confirmation_creates_a_trip(self):
        product = self._product("FTL", cargo_mode="ftl")
        order, line = self._sale(product)
        self.env["tms.cargo"].create(
            {
                "sale_line_id": line.id,
                "name": "Coils",
                "weight": 1000.0,
                "weight_uom_id": self.kilogram.id,
            }
        )
        self.assertFalse(line.tms_order_ids)
        order.action_confirm()
        self.assertEqual(len(line.tms_order_ids), 1)
        trip = line.tms_order_ids
        self.assertEqual(trip.origin_id, self.origin)
        self.assertEqual(trip.destination_id, self.destination)
        self.assertEqual(trip.cargo_ids.sale_line_id, line)
        self.assertEqual(trip.transport_type, "cargo")

    def test_ltl_uses_the_closest_trip(self):
        nearer = self._trip()
        self._trip(
            scheduled_date_start=self.start + timedelta(days=3),
            scheduled_date_end=self.end + timedelta(days=3),
        )
        product = self._product("LTL", cargo_mode="ltl")
        order, line = self._sale(product)
        cargo = self.env["tms.cargo"].create(
            {"sale_line_id": line.id, "name": "Boxes", "weight": 20.0}
        )
        order.action_confirm()
        self.assertEqual(cargo.order_id, nearer)
        self.assertFalse(line.tms_order_ids)

    def test_ltl_creates_a_trip_when_none_match(self):
        product = self._product("LTL", cargo_mode="ltl")
        order, line = self._sale(product)
        cargo = self.env["tms.cargo"].create(
            {"sale_line_id": line.id, "name": "Boxes"}
        )
        order.action_confirm()
        self.assertTrue(cargo.order_id)
        self.assertEqual(cargo.order_id.origin_id, self.origin)

    def test_fcl_skips_a_trip_without_capacity(self):
        brand = self.env["fleet.vehicle.model.brand"].create({"name": "Brand"})
        model = self.env["fleet.vehicle.model"].create(
            {"name": "Truck", "brand_id": brand.id, "vehicle_type": "truck"}
        )
        model.max_weight_capacity = 1000.0
        model.max_weight_uom_id = self.kilogram
        vehicle = self.env["fleet.vehicle"].create(
            {
                "name": "Small truck",
                "model_id": model.id,
                "operation": "cargo",
            }
        )
        full = self._trip(vehicle_id=vehicle.id)
        product = self._product("FCL", cargo_mode="fcl")
        order, line = self._sale(product)
        cargo = self.env["tms.cargo"].create(
            {
                "sale_line_id": line.id,
                "shipment_unit": "container",
                "container_type": "40hc",
                "weight": 18000.0,
                "weight_uom_id": self.kilogram.id,
            }
        )
        order.action_confirm()
        self.assertNotEqual(cargo.order_id, full)
        self.assertTrue(cargo.order_id)

    def test_lcl_uses_a_container_with_room(self):
        trip = self._trip()
        shell = self.env["tms.cargo"].create(
            {
                "name": "Box",
                "shipment_unit": "container",
                "container_type": "20dry",
                "order_id": trip.id,
            }
        )
        product = self._product("LCL", cargo_mode="lcl")
        order, line = self._sale(product)
        cargo = self.env["tms.cargo"].create(
            {
                "sale_line_id": line.id,
                "name": "Cartons",
                "volume": 10.0,
                "volume_uom_id": self.cubic_meter.id,
            }
        )
        order.action_confirm()
        self.assertEqual(cargo.order_id, trip)
        self.assertEqual(cargo.holding_id, shell)

    def test_lcl_creates_a_trip_and_container(self):
        product = self._product("LCL", cargo_mode="lcl")
        order, line = self._sale(product)
        cargo = self.env["tms.cargo"].create(
            {"sale_line_id": line.id, "name": "Cartons", "volume": 10.0}
        )
        order.action_confirm()
        self.assertTrue(cargo.order_id)
        self.assertEqual(cargo.holding_id.shipment_unit, "container")
        self.assertEqual(cargo.holding_id.order_id, cargo.order_id)

    def test_air_consolidation_creates_a_uld(self):
        product = self._product("Air", cargo_mode="air_consolidation")
        order, line = self._sale(product)
        cargo = self.env["tms.cargo"].create(
            {"sale_line_id": line.id, "name": "Parcels", "weight": 100.0}
        )
        order.action_confirm()
        self.assertEqual(cargo.holding_id.shipment_unit, "uld")
        self.assertEqual(cargo.holding_id.uld_type, "ake")

    def test_back_to_back_assigns_the_uld(self):
        trip = self._trip()
        product = self._product("B2B", cargo_mode="back_to_back")
        order, line = self._sale(product)
        cargo = self.env["tms.cargo"].create(
            {
                "sale_line_id": line.id,
                "uld_type": "pmc",
                "uld_number": "PMC12345AB",
                "weight": 500.0,
                "weight_uom_id": self.kilogram.id,
            }
        )
        self.assertEqual(cargo.shipment_unit, "uld")
        order.action_confirm()
        self.assertEqual(cargo.order_id, trip)
        self.assertFalse(cargo.holding_id)

    def test_charter_creates_a_passenger_trip(self):
        product = self._product("Charter", transit_mode="charter")
        order, line = self._sale(product)
        order.action_confirm()
        self.assertEqual(line.tms_trip_ticket_id.transport_type, "passenger")
        self.assertEqual(line.tms_trip_ticket_id.origin_id, self.origin)

    def test_cabin_assigns_a_compartment(self):
        trip = self._trip(transport_type="passenger")
        cabin = self.env["tms.compartment"].create(
            {"name": "Business", "order_id": trip.id, "capacity": 4}
        )
        product = self._product("Cabin", transit_mode="cabin")
        order, line = self._sale(product, qty=2)
        order.action_confirm()
        self.assertEqual(line.tms_compartment_id, cabin)
        self.assertEqual(line.tms_trip_ticket_id, trip)

    def test_seat_assigns_an_available_seat(self):
        brand = self.env["fleet.vehicle.model.brand"].create({"name": "Brand"})
        model = self.env["fleet.vehicle.model"].create(
            {
                "name": "Bus",
                "brand_id": brand.id,
                "passenger_capacity": 2,
            }
        )
        vehicle = self.env["fleet.vehicle"].create(
            {
                "name": "Bus",
                "model_id": model.id,
                "operation": "passenger",
            }
        )
        trip = self._trip(transport_type="passenger", vehicle_id=vehicle.id)
        self.assertEqual(len(trip.seat_ticket_ids), 2)
        product = self._product("Seat", transit_mode="seat")
        order, line = self._sale(product, qty=1)
        order.action_confirm()
        self.assertEqual(line.tms_trip_ticket_id, trip)
        sold = trip.seat_ticket_ids.filtered("sale_line_id")
        self.assertEqual(sold.sale_line_id, line)
        self.assertEqual(sold.available, "not_available")

    def test_seat_without_a_match_raises(self):
        product = self._product("Seat", transit_mode="seat")
        order, _line = self._sale(product)
        with self.assertRaises(UserError):
            order.action_confirm()
