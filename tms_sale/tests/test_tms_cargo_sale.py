# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta

from odoo.exceptions import UserError, ValidationError

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
                "tms_trip": True,
                "trip_product_type": "trip",
                "tms_factor_type": "weight",
                "tms_factor_weight_uom": cls.kilogram.id,
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

    def test_weight_service_quantity_stays_one(self):
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        with self.assertRaises(ValidationError):
            self.env["sale.order.line"].create(
                {"order_id": order.id, **self._line_vals(product_uom_qty=2)}
            )

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
        self.assertEqual(line.tms_factor, 1200.0)
        self.assertEqual(line.cargo_ids.order_id, order.tms_order_ids)

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
        self.assertEqual(line.tms_factor, 950.0)

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
        self.assertEqual(line.tms_factor, 300.0)
        arch = self.env["sale.order"].get_view(view_type="form")["arch"]
        self.assertIn("tms_factor_type != 'weight'", arch)
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
        self.assertEqual(line.tms_factor, 1200.0)
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
        self.assertEqual(line_a.tms_factor, 500.0)
        self.assertEqual(line_b.tms_factor, 300.0)
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
        self.assertEqual(line_a.tms_factor, 500.0)
        order_b.action_confirm()
        self.assertEqual(trip_a.stage_id, self.env.ref("tms.tms_stage_order_draft"))

    def test_started_trip_refuses_a_cargo_move(self):
        order, _line, cargo = self._order_with_cargo(200.0, "Coils")
        brand = self.env["fleet.vehicle.model.brand"].create({"name": "Split Brand"})
        model = self.env["fleet.vehicle.model"].create(
            {"name": "Split Model", "brand_id": brand.id}
        )
        vehicle = self.env["fleet.vehicle"].create(
            {
                "model_id": model.id,
                "operation": "cargo",
                "capacity": 20.0,
                "cargo_uom_id": self.env.ref("uom.product_uom_cubic_meter").id,
            }
        )
        trip = order.tms_order_ids
        trip.vehicle_id = vehicle
        cargo.volume = 1.0
        cargo.volume_uom_id = vehicle.cargo_uom_id
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
