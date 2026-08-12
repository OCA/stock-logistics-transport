# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta

from odoo.addons.base.tests.common import BaseCommon


class TestTmsSale(BaseCommon):
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
        cls.trip_template = cls.env["product.template"].create(
            {
                "name": "Trip Service",
                "type": "service",
                "list_price": 100.0,
            }
        )
        cls.trip_template.write(
            {
                "tms_trip": True,
                "trip_product_type": "trip",
                "tms_factor_type": "distance",
                "tms_factor_distance_uom": cls.env.ref("uom.product_uom_meter").id,
            }
        )
        cls.env.flush_all()
        cls.trip_product = cls.trip_template.product_variant_ids[0]
        cls.start = datetime.now()
        cls.end = cls.start + timedelta(hours=2)

    def _create_sale_order_line_vals(self):
        return {
            "product_id": self.trip_product.id,
            "product_uom_qty": 1,
            "tms_origin_id": self.origin.id,
            "tms_destination_id": self.destination.id,
            "tms_scheduled_date_start": self.start,
            "tms_scheduled_date_end": self.end,
        }

    def _create_order_with_trip_line(self):
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        self.env["sale.order.line"].create(
            {"order_id": order.id, **self._create_sale_order_line_vals()}
        )
        order._refresh_tms_trip_lines()
        order._action_create_new_trips()
        order.invalidate_recordset(["tms_order_ids", "tms_order_count"])
        return order

    def test_has_trip_product_compute(self):
        line = self.env["sale.order.line"].create(
            {
                "order_id": self.env["sale.order"]
                .create({"partner_id": self.partner.id})
                .id,
                **self._create_sale_order_line_vals(),
            }
        )
        line._compute_sale_order_line_tms()
        self.assertTrue(line.has_trip_product)

    def test_prepare_tms_values(self):
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        line = self.env["sale.order.line"].create(
            {"order_id": order.id, **self._create_sale_order_line_vals()}
        )
        vals = line._prepare_tms_values(so_id=order.id, sol_id=line.id)
        self.assertEqual(vals["sale_id"], order.id)
        self.assertEqual(vals["sale_line_id"], line.id)
        self.assertEqual(vals["origin_id"], self.origin.id)
        self.assertEqual(vals["destination_id"], self.destination.id)
        self.assertEqual(vals["scheduled_duration"], 2.0)

    def test_sale_order_creates_tms_orders(self):
        order = self._create_order_with_trip_line()
        self.assertEqual(order.tms_order_count, 1)
        self.assertEqual(order.tms_order_ids.sale_line_id, order.order_line)

    def test_sale_order_state_updates_tms_stage(self):
        order = self._create_order_with_trip_line()
        tms_order = order.tms_order_ids
        draft_stage = self.env.ref("tms.tms_stage_order_draft")
        self.assertEqual(tms_order.stage_id, draft_stage)

        order.action_confirm()
        confirmed_stage = self.env.ref("tms.tms_stage_order_confirmed")
        self.assertEqual(tms_order.stage_id, confirmed_stage)

    def test_action_view_tms_order_no_orders(self):
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        action = order.action_view_tms_order()
        self.assertEqual(action["type"], "ir.actions.act_window_close")

    def test_action_view_tms_order_single_order(self):
        order = self._create_order_with_trip_line()
        action = order.action_view_tms_order()
        self.assertEqual(action["res_id"], order.tms_order_ids.id)

    def test_action_view_trip_sale_order_line(self):
        action = self.env["sale.order"].action_view_trip_sale_order_line()
        self.assertEqual(action["res_model"], "sale.order.line.trip")
        self.assertEqual(action["view_mode"], "form")

    def test_sale_order_cancel_updates_tms_stage(self):
        order = self._create_order_with_trip_line()
        tms_order = order.tms_order_ids
        order.action_cancel()
        cancelled_stage = self.env.ref("tms.tms_stage_order_cancelled")
        self.assertEqual(tms_order.stage_id, cancelled_stage)

    def test_remove_line_deletes_tms_order(self):
        order = self._create_order_with_trip_line()
        line = order.order_line
        tms_order = order.tms_order_ids
        order.write({"order_line": [(2, line.id, 0)]})
        self.assertFalse(tms_order.exists())

    def test_line_write_syncs_tms_order_fields(self):
        order = self._create_order_with_trip_line()
        line = order.order_line
        tms_order = order.tms_order_ids
        new_origin = self.env["res.partner"].create(
            {"name": "New Origin", "tms_location": True}
        )
        line.write({"tms_origin_id": new_origin.id})
        self.assertEqual(tms_order.origin_id, new_origin)

    def test_create_with_embedded_order_line(self):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [(0, 0, self._create_sale_order_line_vals())],
            }
        )
        self.assertEqual(order.tms_order_count, 1)

    def test_compute_amount_with_tms_factor(self):
        line = self.env["sale.order.line"].create(
            {
                "order_id": self.env["sale.order"]
                .create({"partner_id": self.partner.id})
                .id,
                **self._create_sale_order_line_vals(),
            }
        )
        line._compute_sale_order_line_tms()
        tax_base = line._prepare_base_line_for_taxes_computation()
        self.assertEqual(tax_base["quantity"], line.product_uom_qty * line.tms_factor)

    def test_seat_product_compute(self):
        seat_template = self.env["product.template"].create(
            {"name": "Seat", "type": "service", "list_price": 25.0}
        )
        seat_template.write({"tms_trip": True, "trip_product_type": "seat"})
        line = self.env["sale.order.line"].new(
            {
                "order_id": self.env["sale.order"].new({"partner_id": self.partner.id}),
                "product_id": seat_template.product_variant_ids,
                "product_uom_qty": 1,
            }
        )
        line._compute_sale_order_line_tms()
        self.assertTrue(line.seat_ticket)
        self.assertFalse(line.has_trip_product)

    def test_has_tms_order_compute(self):
        order = self._create_order_with_trip_line()
        self.assertTrue(order.has_tms_order)

    def test_tms_order_count_includes_seat_line_trip(self):
        seat_template = self.env["product.template"].create(
            {"name": "Seat", "type": "service", "list_price": 25.0}
        )
        seat_template.write({"tms_trip": True, "trip_product_type": "seat"})
        tms_trip = self.env["tms.order"].create(
            {
                "name": "PASSENGER-TRIP",
                "company_id": self.env.company.id,
                "origin_id": self.origin.id,
                "destination_id": self.destination.id,
            }
        )
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        self.env["sale.order.line"].create(
            {
                "order_id": order.id,
                "product_id": seat_template.product_variant_ids.id,
                "product_uom_qty": 1,
                "tms_trip_ticket_id": tms_trip.id,
            }
        )
        order.invalidate_recordset(["tms_order_ids", "tms_order_count"])
        self.assertIn(tms_trip, order.tms_order_ids)
        self.assertEqual(order.tms_order_count, 1)

    def test_action_view_tms_order_multiple_orders(self):
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        self.env["sale.order.line"].create(
            {
                "order_id": order.id,
                **self._create_sale_order_line_vals(),
                "product_uom_qty": 2,
            }
        )
        order._refresh_tms_trip_lines()
        order._action_create_new_trips()
        order.invalidate_recordset(["tms_order_ids", "tms_order_count"])
        self.assertEqual(order.tms_order_count, 2)
        action = order.action_view_tms_order()
        self.assertEqual(action["domain"], [("id", "in", order.tms_order_ids.ids)])

    def test_decrease_qty_removes_tms_order(self):
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        line = self.env["sale.order.line"].create(
            {
                "order_id": order.id,
                **self._create_sale_order_line_vals(),
                "product_uom_qty": 2,
            }
        )
        order._refresh_tms_trip_lines()
        order._action_create_new_trips()
        order.invalidate_recordset(["tms_order_ids", "tms_order_count"])
        tms_orders = order.tms_order_ids
        self.assertEqual(len(tms_orders), 2)
        order.write({"order_line": [(1, line.id, {"product_uom_qty": 1})]})
        self.assertEqual(len(order.tms_order_ids), 1)
        self.assertEqual(len(tms_orders.exists()), 1)

    def test_post_tms_message(self):
        order = self._create_order_with_trip_line()
        tms_order = order.tms_order_ids
        initial_messages = len(order.message_ids)
        order._post_tms_message(tms_order)
        self.assertGreater(len(order.message_ids), initial_messages)

    def test_state_non_sale_resets_tms_stage_to_draft(self):
        order = self._create_order_with_trip_line()
        tms_order = order.tms_order_ids
        order.action_confirm()
        order.sudo().write({"state": "sent"})
        draft_stage = self.env.ref("tms.tms_stage_order_draft")
        self.assertEqual(tms_order.stage_id, draft_stage)

    def test_driver_action_view_sale_orders_uses_partner_id(self):
        """The driver smart button must resolve the driver's partner id
        (delegation inheritance), not the driver id."""
        driver = self.env["tms.driver"].create({"name": "Driver Sale"})
        action = driver.action_view_sale_orders()
        self.assertEqual(action["res_model"], "sale.order")
        self.assertEqual(
            action["context"]["default_partner_id"],
            driver.partner_id.id,
        )
        self.assertNotEqual(
            action["context"]["default_partner_id"],
            driver.id,
            "Must use partner id, not driver id",
        )
