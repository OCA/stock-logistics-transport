# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta

from odoo.exceptions import UserError

from odoo.addons.base.tests.common import BaseCommon


class TestTMSCargoSale(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.partner = cls.env["res.partner"].create({"name": "Cargo Customer"})
        cls.origin = cls.env["res.partner"].create(
            {"name": "Cargo Origin", "tms_location": True}
        )
        cls.destination = cls.env["res.partner"].create(
            {"name": "Cargo Destination", "tms_location": True}
        )
        cls.kilogram = cls.env.ref("uom.product_uom_kgm")
        cls.template = cls.env["product.template"].create(
            {
                "name": "TMS Cargo Service Test",
                "type": "service",
                "list_price": 1.0,
            }
        )
        cls.template.write(
            {
                "transport_type": "cargo",
                "transit_mode": "road",
                "booking_type": "full_asset",
            }
        )
        cls.product = cls.template.product_variant_ids[0]
        cls.start = datetime.now()
        cls.end = cls.start + timedelta(hours=4)

    def _line_vals(self, **extra):
        values = {
            "product_id": self.product.id,
            "product_uom_qty": 1,
            "tms_origin_id": self.origin.id,
            "tms_destination_id": self.destination.id,
            "tms_scheduled_date_start": self.start,
            "tms_scheduled_date_end": self.end,
        }
        values.update(extra)
        return values

    def test_shipment_quantity_follows_the_sale_uom(self):
        unit = self.env.ref("uom.product_uom_unit")
        pallet = self.env.ref("tms.uom_pallet")
        cubic = self.env.ref("uom.product_uom_cubic_meter")
        tonne = self.env.ref("uom.product_uom_ton")
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        line = self.env["sale.order.line"].create(
            {"order_id": order.id, **self._line_vals()}
        )
        self.env["tms.cargo"].create(
            {
                "name": "Boxes",
                "sale_line_id": line.id,
                "quantity": 3,
                "uom_id": unit.id,
                "weight": 500.0,
                "weight_uom_id": self.kilogram.id,
                "volume": 2.0,
                "volume_uom_id": cubic.id,
            }
        )
        self.env["tms.cargo"].create(
            {
                "name": "Pallets",
                "sale_line_id": line.id,
                "quantity": 2,
                "uom_id": pallet.id,
                "weight": 1.5,
                "weight_uom_id": tonne.id,
                "volume": 4.0,
                "volume_uom_id": cubic.id,
            }
        )
        self.assertIn(pallet, line.allowed_uom_ids)
        self.assertIn(self.kilogram, line.allowed_uom_ids)
        self.assertEqual(line.product_uom_qty, 3.0)
        line.product_uom_id = pallet
        self.assertEqual(line.product_uom_qty, 2.0)
        line.product_uom_id = self.kilogram
        self.assertEqual(line.product_uom_qty, 2000.0)
        line.product_uom_id = cubic
        self.assertEqual(line.product_uom_qty, 6.0)

    def test_cargo_sets_factor_and_links_one_trip(self):
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        line = self.env["sale.order.line"].create(
            {"order_id": order.id, **self._line_vals()}
        )
        self.env["tms.cargo"].create(
            {
                "name": "Steel coils",
                "sale_line_id": line.id,
                "weight": 800.0,
                "weight_uom_id": self.kilogram.id,
            }
        )
        self.env["tms.cargo"].create(
            {
                "name": "Spare parts",
                "sale_line_id": line.id,
                "weight": 400.0,
                "weight_uom_id": self.kilogram.id,
            }
        )
        order._refresh_tms_trip_lines()
        order._action_create_new_trips()
        order.invalidate_recordset(["tms_order_ids", "tms_order_count"])
        self.assertEqual(order.tms_order_count, 1)
        self.assertEqual(line.cargo_ids.order_id, order.tms_order_ids)
        trip = order.tms_order_ids
        self.assertEqual(trip.shipment_line_count, 2)
        action = trip.action_view_shipment_lines()
        self.assertEqual(set(action["domain"][0][2]), set(line.cargo_ids.ids))

    def test_confirmed_sale_keeps_factor_in_sync_from_the_trip(self):
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        line = self.env["sale.order.line"].create(
            {"order_id": order.id, **self._line_vals()}
        )
        cargo = self.env["tms.cargo"].create(
            {
                "name": "Steel coils",
                "sale_line_id": line.id,
                "weight": 800.0,
                "weight_uom_id": self.kilogram.id,
            }
        )
        order._refresh_tms_trip_lines()
        order._action_create_new_trips()
        order.action_confirm()
        cargo.weight = 950.0
        self.assertEqual(cargo.weight, 950.0)

    def test_cargo_added_on_the_trip_updates_the_factor(self):
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        line = self.env["sale.order.line"].create(
            {"order_id": order.id, **self._line_vals()}
        )
        order._refresh_tms_trip_lines()
        order._action_create_new_trips()
        self.env["tms.cargo"].create(
            {
                "name": "Steel coils",
                "order_id": order.tms_order_ids.id,
                "weight": 300.0,
                "weight_uom_id": self.kilogram.id,
            }
        )
        self.assertEqual(line.cargo_ids.sale_line_id, line)
        arch = self.env["sale.order"].get_view(view_type="form")["arch"]
        self.assertIn("not has_trip_product", arch)
        self.assertNotIn("tms_factor", arch)
        self.assertIn('string="Cargo"', arch)
        wizard = self.env.ref("tms_sale.sale_order_line_trip_view_form").arch
        self.assertIn("cargo_line_ids", wizard)
        self.assertIn("Pickup date", wizard)
        self.assertIn("Delivery date", wizard)
        self.assertIn('name="distance"', wizard)
        self.assertIn("parent.state in ('sale', 'cancel')", arch)

    def _order_with_cargo(self, weight, description):
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        line = self.env["sale.order.line"].create(
            {"order_id": order.id, **self._line_vals()}
        )
        cargo = self.env["tms.cargo"].create(
            {
                "name": description,
                "sale_line_id": line.id,
                "weight": weight,
                "weight_uom_id": self.kilogram.id,
            }
        )
        order._refresh_tms_trip_lines()
        order._action_create_new_trips()
        return order, line, cargo

    def test_split_trip_keeps_the_sale_and_the_weight(self):
        order, line, heavy = self._order_with_cargo(800.0, "Steel coils")
        light = self.env["tms.cargo"].create(
            {
                "name": "Spare parts",
                "sale_line_id": line.id,
                "weight": 400.0,
                "weight_uom_id": self.kilogram.id,
            }
        )
        trip = order.tms_order_ids
        action = trip.action_split_trip()
        new_trip = self.env["tms.order"].browse(action["res_id"])
        self.assertEqual(new_trip.sale_line_id, line)
        self.assertEqual(new_trip.sale_id, order)
        self.assertEqual(new_trip.stage_id, trip.stage_id)
        self.assertFalse(new_trip.cargo_ids)
        light.order_id = new_trip
        self.assertEqual(light.sale_line_id, line)
        self.assertEqual(heavy.order_id, trip)
        self.assertEqual(order.tms_order_count, 2)
        completed = self.env.ref("tms.tms_stage_order_completed")
        trip.stage_id = completed
        self.assertEqual(line.qty_delivered, 0.0)
        new_trip.stage_id = completed
        self.assertEqual(line.qty_delivered, line.product_uom_qty)

    def test_shared_truck_keeps_each_sale(self):
        order_a, line_a, cargo_a = self._order_with_cargo(500.0, "Coils")
        order_b, line_b, cargo_b = self._order_with_cargo(300.0, "Parts")
        trip_a = order_a.tms_order_ids
        cargo_b.order_id = trip_a
        self.assertEqual(cargo_a.sale_line_id, line_a)
        self.assertEqual(cargo_b.sale_line_id, line_b)
        self.assertEqual(cargo_a.weight, 500.0)
        self.assertEqual(cargo_b.weight, 300.0)
        self.assertIn(trip_a, order_b.tms_order_ids)
        self.assertEqual(trip_a.cargo_sale_order_count, 2)
        action = trip_a.action_view_sales()
        self.assertEqual(set(action["domain"][0][2]), {order_a.id, order_b.id})
        loose = self.env["tms.cargo"].create(
            {
                "name": "Unassigned",
                "order_id": trip_a.id,
                "weight": 10.0,
                "weight_uom_id": self.kilogram.id,
            }
        )
        self.assertFalse(loose.sale_line_id)
        self.assertEqual(cargo_a.weight, 500.0)
        order_b.action_confirm()
        self.assertEqual(trip_a.stage_id, self.env.ref("tms.tms_stage_order_draft"))

    def test_started_trip_refuses_a_cargo_move(self):
        order, _line, cargo = self._order_with_cargo(200.0, "Coils")
        brand = self.env["fleet.vehicle.model.brand"].create({"name": "Split Brand"})
        model = self.env["fleet.vehicle.model"].create(
            {"name": "Split Model", "brand_id": brand.id}
        )
        cubic_meter = self.env.ref("uom.product_uom_cubic_meter")
        model.max_volume_capacity = 20.0
        model.max_volume_uom_id = cubic_meter
        vehicle = self.env["fleet.vehicle"].create(
            {
                "model_id": model.id,
                "operation": "cargo",
            }
        )
        trip = order.tms_order_ids
        trip.vehicle_id = vehicle
        cargo.volume = 1.0
        cargo.volume_uom_id = cubic_meter
        trip.stage_id = self.env.ref("tms.tms_stage_order_confirmed")
        cargo.state = "loaded"
        trip.button_start_order()
        other = self.env["tms.order"].create(
            {
                "origin_id": self.origin.id,
                "destination_id": self.destination.id,
                "vehicle_id": vehicle.id,
            }
        )
        with self.assertRaises(UserError):
            cargo.order_id = other

    def test_description_summarizes_cargo_and_distance(self):
        route = self.env["tms.route"].create(
            {
                "name": "Cargo Route",
                "origin_location_id": self.origin.id,
                "destination_location_id": self.destination.id,
                "distance": 120.0,
                "estimated_time": 2.0,
                "distance_uom": self.env.ref("uom.product_uom_km").id,
                "estimated_time_uom": self.env.ref("uom.product_uom_hour").id,
            }
        )
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        line = self.env["sale.order.line"].create(
            {
                "order_id": order.id,
                **self._line_vals(tms_route_id=route.id, tms_route_flag=True),
            }
        )
        self.env["tms.cargo"].create(
            {
                "name": "Steel coils",
                "sale_line_id": line.id,
                "quantity": 4,
                "weight": 800.0,
                "weight_uom_id": self.kilogram.id,
                "packaging": "Pallets",
            }
        )
        self.assertIn("Origin: Cargo Origin", line.name)
        self.assertIn("Destination: Cargo Destination", line.name)
        self.assertIn("Distance: 120.00", line.name)
        self.assertIn("Cargo:", line.name)
        self.assertIn("Steel coils", line.name)
        self.assertIn("800.00 kg", line.name)
        self.assertIn("Pallets", line.name)
        self.assertIn("Pickup:", line.name)
        self.assertIn("Delivery:", line.name)

    def test_description_summarizes_container(self):
        self.template.write({"transit_mode": "water", "booking_type": "full_asset"})
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        line = self.env["sale.order.line"].create(
            {"order_id": order.id, **self._line_vals()}
        )
        cargo = self.env["tms.cargo"].create(
            {
                "sale_line_id": line.id,
                "shipment_unit": "container",
                "container_type": "40hc",
                "container_number": "MSCU1234567",
                "seal_number": "SL123",
                "quantity": 2,
                "weight": 18000.0,
                "weight_uom_id": self.kilogram.id,
            }
        )
        self.assertEqual(cargo.shipment_unit, "container")
        self.assertIn("40' High Cube", cargo.name)
        self.assertIn("Containers:", line.name)
        self.assertIn("2 x 40' High Cube", line.name)
        self.assertIn("MSCU1234567", line.name)
        self.assertIn("seal SL123", line.name)

    def test_description_uses_container_fields_when_unit_is_cargo(self):
        self.template.write({"transit_mode": "water", "booking_type": "full_asset"})
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        line = self.env["sale.order.line"].create(
            {"order_id": order.id, **self._line_vals()}
        )
        self.env["tms.cargo"].create(
            {
                "sale_line_id": line.id,
                "shipment_unit": "cargo",
                "container_type": "40hc",
                "container_number": "MSCU1234567",
                "seal_number": "SL123",
                "quantity": 1,
                "weight": 18000.0,
                "weight_uom_id": self.kilogram.id,
            }
        )
        self.assertIn("Containers:", line.name)
        self.assertIn("1 x 40' High Cube", line.name)
        self.assertIn("MSCU1234567", line.name)
        self.assertNotIn("Cargo:", line.name)

    def test_description_summarizes_uld(self):
        self.template.write({"transit_mode": "air", "booking_type": "shared_space"})
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        line = self.env["sale.order.line"].create(
            {"order_id": order.id, **self._line_vals()}
        )
        cargo = self.env["tms.cargo"].create(
            {
                "sale_line_id": line.id,
                "uld_type": "ake",
                "uld_number": "AKE12345AB",
                "quantity": 1,
                "weight": 450.0,
                "weight_uom_id": self.kilogram.id,
            }
        )
        self.assertEqual(cargo.shipment_unit, "uld")
        self.assertIn("ULD:", line.name)
        self.assertIn("1 x AKE (LD3)", line.name)
        self.assertIn("AKE12345AB", line.name)
