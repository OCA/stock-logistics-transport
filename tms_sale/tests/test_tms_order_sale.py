# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.base.tests.common import BaseCommon


class TestTmsOrderSale(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.partner = cls.env["res.partner"].create({"name": "Customer"})
        cls.origin = cls.env["res.partner"].create(
            {"name": "Origin", "tms_location": True}
        )
        cls.destination = cls.env["res.partner"].create(
            {"name": "Destination", "tms_location": True}
        )
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
                "capacity": 3,
                "tms_service_product_id": cls.env.ref(
                    "tms_product.product_tms_seat_service"
                )
                .product_variant_ids[0]
                .id,
            }
        )
        cls.sale_order = cls.env["sale.order"].create({"partner_id": cls.partner.id})
        cls.trip_template = cls.env["product.template"].create(
            {"name": "Trip", "type": "service", "list_price": 50.0}
        )
        cls.trip_template.write({"tms_trip": True, "trip_product_type": "trip"})
        cls.sale_line = cls.env["sale.order.line"].create(
            {
                "order_id": cls.sale_order.id,
                "product_id": cls.trip_template.product_variant_ids.id,
                "product_uom_qty": 2,
            }
        )

    def _create_tms_order(self, **extra):
        return self.env["tms.order"].create(
            {
                "name": "ORDER-TEST",
                "company_id": self.env.company.id,
                "origin_id": self.origin.id,
                "destination_id": self.destination.id,
                "sale_id": self.sale_order.id,
                "sale_line_id": self.sale_line.id,
                **extra,
            }
        )

    def test_action_view_sales(self):
        tms_order = self._create_tms_order()
        action = tms_order.action_view_sales()
        self.assertEqual(action["res_model"], "sale.order")
        self.assertEqual(action["res_id"], self.sale_order.id)

    def test_passenger_vehicle_creates_seat_tickets_on_create(self):
        tms_order = self._create_tms_order(vehicle_id=self.passenger_vehicle.id)
        self.assertEqual(len(tms_order.seat_ticket_ids), 3)
        seat_product = self.passenger_vehicle.tms_service_product_id
        for ticket in tms_order.seat_ticket_ids:
            self.assertTrue(ticket.name)
            self.assertEqual(ticket.product_id, seat_product)
            self.assertEqual(ticket.price, seat_product.lst_price)

    def test_passenger_vehicle_creates_seat_tickets_on_write(self):
        tms_order = self._create_tms_order()
        tms_order.write({"vehicle_id": self.passenger_vehicle.id})
        self.assertEqual(len(tms_order.seat_ticket_ids), 3)
        seat_product = self.passenger_vehicle.tms_service_product_id
        self.assertEqual(tms_order.seat_ticket_ids.product_id, seat_product)
        self.assertTrue(
            all(
                ticket.price == seat_product.lst_price
                for ticket in tms_order.seat_ticket_ids
            )
        )

    def test_completed_stage_sets_qty_delivered(self):
        tms_order = self._create_tms_order()
        completed_stage = self.env.ref("tms.tms_stage_order_completed")
        tms_order.write({"stage_id": completed_stage.id})
        self.assertEqual(self.sale_line.qty_delivered, self.sale_line.product_uom_qty)

    def test_action_view_sales_from_sale_id(self):
        tms_order = self.env["tms.order"].create(
            {
                "name": "ORDER-SALE-ID",
                "company_id": self.env.company.id,
                "origin_id": self.origin.id,
                "destination_id": self.destination.id,
                "sale_id": self.sale_order.id,
            }
        )
        action = tms_order.action_view_sales()
        self.assertEqual(action["res_id"], self.sale_order.id)

    def test_non_passenger_vehicle_skips_seat_tickets(self):
        cargo_vehicle = self.env["fleet.vehicle"].create(
            {
                "name": "Cargo Truck",
                "model_id": self.vehicle_model.id,
                "operation": "cargo",
                "capacity": 3,
            }
        )
        tms_order = self._create_tms_order(vehicle_id=cargo_vehicle.id)
        self.assertFalse(tms_order.seat_ticket_ids)

    def test_seat_ticket_unlink_command_on_write(self):
        tms_order = self._create_tms_order(vehicle_id=self.passenger_vehicle.id)
        ticket = tms_order.seat_ticket_ids[:1]
        self.assertTrue(ticket)
        tms_order.write({"seat_ticket_ids": [(2, ticket.id)]})
        self.assertFalse(ticket.exists())

    def test_passenger_vehicle_change_updates_ticket_count(self):
        large_bus = self.env["fleet.vehicle"].create(
            {
                "name": "Large Bus",
                "model_id": self.vehicle_model.id,
                "operation": "passenger",
                "capacity": 5,
            }
        )
        tms_order = self._create_tms_order(vehicle_id=self.passenger_vehicle.id)
        self.assertEqual(len(tms_order.seat_ticket_ids), 3)
        tms_order.write({"vehicle_id": large_bus.id})
        self.assertEqual(len(tms_order.seat_ticket_ids), 5)

    def test_clearing_vehicle_removes_available_tickets(self):
        tms_order = self._create_tms_order(vehicle_id=self.passenger_vehicle.id)
        self.assertEqual(len(tms_order.seat_ticket_ids), 3)
        tms_order.write({"vehicle_id": False})
        self.assertFalse(tms_order.seat_ticket_ids)

    def test_seat_sale_order_count_from_sold_tickets(self):
        tms_order = self._create_tms_order(vehicle_id=self.passenger_vehicle.id)
        sale_order_a = self.env["sale.order"].create({"partner_id": self.partner.id})
        sale_line_a = self.env["sale.order.line"].create(
            {
                "order_id": sale_order_a.id,
                "name": "Seat line A",
                "product_uom_qty": 1,
            }
        )
        sale_order_b = self.env["sale.order"].create({"partner_id": self.partner.id})
        sale_line_b = self.env["sale.order.line"].create(
            {
                "order_id": sale_order_b.id,
                "name": "Seat line B",
                "product_uom_qty": 1,
            }
        )
        tms_order.seat_ticket_ids[0].write({"sale_line_id": sale_line_a.id})
        tms_order.seat_ticket_ids[1].write({"sale_line_id": sale_line_b.id})
        tms_order.invalidate_recordset(["seat_sale_order_ids", "seat_sale_order_count"])
        self.assertEqual(tms_order.seat_sale_order_count, 2)
        self.assertIn(sale_order_a, tms_order.seat_sale_order_ids)
        self.assertIn(sale_order_b, tms_order.seat_sale_order_ids)

    def test_action_view_seat_sale_orders_single(self):
        tms_order = self._create_tms_order(vehicle_id=self.passenger_vehicle.id)
        tms_order.seat_ticket_ids[0].write({"sale_line_id": self.sale_line.id})
        tms_order.invalidate_recordset(["seat_sale_order_ids", "seat_sale_order_count"])
        action = tms_order.action_view_seat_sale_orders()
        self.assertEqual(action["res_id"], self.sale_order.id)

    def test_action_view_seat_sale_orders_multiple(self):
        tms_order = self._create_tms_order(vehicle_id=self.passenger_vehicle.id)
        sale_order_b = self.env["sale.order"].create({"partner_id": self.partner.id})
        sale_line_b = self.env["sale.order.line"].create(
            {
                "order_id": sale_order_b.id,
                "name": "Seat line B",
                "product_uom_qty": 1,
            }
        )
        tms_order.seat_ticket_ids[0].write({"sale_line_id": self.sale_line.id})
        tms_order.seat_ticket_ids[1].write({"sale_line_id": sale_line_b.id})
        tms_order.invalidate_recordset(["seat_sale_order_ids", "seat_sale_order_count"])
        action = tms_order.action_view_seat_sale_orders()
        self.assertEqual(
            action["domain"],
            [("id", "in", tms_order.seat_sale_order_ids.ids)],
        )

    def test_action_view_seat_sale_orders_empty(self):
        tms_order = self._create_tms_order(vehicle_id=self.passenger_vehicle.id)
        action = tms_order.action_view_seat_sale_orders()
        self.assertEqual(action["type"], "ir.actions.act_window_close")
