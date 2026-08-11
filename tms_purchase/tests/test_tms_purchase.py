# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.base.tests.common import BaseCommon


class TestTmsPurchase(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        cls.partner = cls.env["res.partner"].create({"name": "Purchase Vendor"})
        cls.origin = cls.env["res.partner"].create(
            {"name": "Origin", "tms_location": True}
        )
        cls.destination = cls.env["res.partner"].create(
            {"name": "Destination", "tms_location": True}
        )
        cls.vehicle_model = cls.env["fleet.vehicle.model"].create(
            {
                "name": "Test Model",
                "brand_id": cls.env["fleet.vehicle.model.brand"]
                .create({"name": "Test Brand"})
                .id,
            }
        )
        cls.trip = cls.env["tms.order"].create(
            {
                "name": "Trip Purchase Test",
                "origin_id": cls.origin.id,
                "destination_id": cls.destination.id,
            }
        )
        cls.purchase = cls.env["purchase.order"].create(
            {
                "partner_id": cls.partner.id,
                "trip_id": cls.trip.id,
            }
        )
        cls.vehicle = cls.env["fleet.vehicle"].create(
            {
                "name": "Linked Vehicle",
                "model_id": cls.vehicle_model.id,
                "purchase_order_id": cls.purchase.id,
            }
        )
        cls.vehicle2 = cls.env["fleet.vehicle"].create(
            {
                "name": "Linked Vehicle 2",
                "model_id": cls.vehicle_model.id,
                "purchase_order_id": cls.purchase.id,
            }
        )

    def test_purchase_order_vehicle_counts(self):
        self.assertEqual(self.purchase.vehicle_count, 2)
        self.assertEqual(self.purchase.order_vehicle_count, 2)

    def test_purchase_order_action_view_order(self):
        action = self.purchase.action_view_order()
        self.assertEqual(action["res_model"], "tms.order")
        self.assertEqual(action["res_id"], self.trip.id)
        self.assertEqual(action["view_mode"], "form")

    def test_purchase_order_action_view_vehicle_single(self):
        vehicle = self.env["fleet.vehicle"].create(
            {
                "name": "Single Vehicle",
                "model_id": self.vehicle_model.id,
                "purchase_order_id": self.purchase.id,
            }
        )
        self.purchase.vehicle_ids = [(6, 0, [vehicle.id])]
        action = self.purchase.action_view_vehicle()
        self.assertEqual(action["res_model"], "fleet.vehicle")
        self.assertEqual(action["res_id"], vehicle.id)
        self.assertEqual(action["view_mode"], "form")

    def test_purchase_order_action_view_vehicle_multiple(self):
        action = self.purchase.action_view_vehicle(vehicles=self.purchase.vehicle_ids)
        self.assertEqual(action["res_model"], "fleet.vehicle")
        self.assertEqual(
            action["domain"], [("id", "in", self.purchase.vehicle_ids.ids)]
        )

    def test_purchase_order_action_view_vehicle_empty(self):
        purchase = self.env["purchase.order"].create({"partner_id": self.partner.id})
        action = purchase.action_view_vehicle(vehicles=self.env["fleet.vehicle"])
        self.assertEqual(action["type"], "ir.actions.act_window_close")

    def test_purchase_order_action_view_vehicles_button(self):
        action = self.purchase.action_view_vehicles_button()
        self.assertEqual(action["res_model"], "fleet.vehicle")
        self.assertEqual(action["view_mode"], "list,form")
        self.assertEqual(
            action["domain"], [("purchase_order_id", "=", self.purchase.id)]
        )

    def test_tms_order_purchase_count(self):
        self.assertEqual(self.trip.purchase_order_count, 1)

    def test_tms_order_action_view_purchase_orders(self):
        action = self.trip.action_view_purchase_orders()
        self.assertEqual(action["res_model"], "purchase.order")
        self.assertEqual(action["view_mode"], "list,form")
        self.assertEqual(action["domain"], [("trip_id", "=", self.trip.id)])
        self.assertEqual(action["context"]["default_trip_id"], self.trip.id)
        self.assertEqual(
            action["context"]["list_view_ref"],
            "tms_purchase.tms_custom_purchase_order_tree",
        )

    def test_tms_order_create_links_purchases(self):
        purchase = self.env["purchase.order"].create({"partner_id": self.partner.id})
        trip = self.env["tms.order"].create(
            {
                "name": "Trip With Purchases",
                "origin_id": self.origin.id,
                "destination_id": self.destination.id,
                "purchase_ids": [(4, purchase.id)],
            }
        )
        self.assertEqual(purchase.trip_id, trip)

    def test_driver_action_view_purchase_orders_uses_partner_id(self):
        """The driver smart button must resolve the driver's partner id
        (delegation inheritance), not the driver id."""
        driver = self.env["tms.driver"].create({"name": "Driver Purchase"})
        action = driver.action_view_purchase_orders()
        self.assertEqual(action["res_model"], "purchase.order")
        self.assertEqual(
            action["context"]["search_default_partner_id"],
            driver.partner_id.id,
        )
        self.assertEqual(
            action["context"]["default_partner_id"],
            driver.partner_id.id,
        )
        self.assertNotEqual(
            action["context"]["search_default_partner_id"],
            driver.id,
            "Must use partner id, not driver id",
        )

    def test_fleet_vehicle_action_view_order(self):
        action = self.vehicle.action_view_order()
        self.assertEqual(action["res_model"], "purchase.order")
        self.assertEqual(action["res_id"], self.purchase.id)
        self.assertEqual(action["view_mode"], "form")

    def test_stock_move_prepare_vehicle_values(self):
        product = self.env["product.product"].create(
            {
                "name": "Vehicle Product",
                "type": "consu",
                "tracking": "serial",
                "tms_vehicle": True,
                "vehicle_type": "car",
                "model_id": self.vehicle_model.id,
            }
        )
        self.purchase.write({"date_order": "2024-06-01 08:00:00"})
        purchase_line = self.env["purchase.order.line"].create(
            {
                "order_id": self.purchase.id,
                "product_id": product.id,
                "product_qty": 1,
                "price_unit": 25000,
            }
        )
        lot = self.env["stock.lot"].create(
            {
                "name": "LOT001",
                "product_id": product.id,
            }
        )
        picking_type = self.env.ref("stock.picking_type_in")
        supplier_location = self.env.ref("stock.stock_location_suppliers")
        stock_location = self.env.ref("stock.stock_location_stock")
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "location_id": supplier_location.id,
                "location_dest_id": stock_location.id,
            }
        )
        move = self.env["stock.move"].create(
            {
                "product_id": product.id,
                "product_uom": product.uom_id.id,
                "product_uom_qty": 1,
                "picking_id": picking.id,
                "location_id": supplier_location.id,
                "location_dest_id": stock_location.id,
                "purchase_line_id": purchase_line.id,
                "origin": self.purchase.name,
            }
        )
        move_line = self.env["stock.move.line"].create(
            {
                "move_id": move.id,
                "product_id": product.id,
                "product_uom_id": product.uom_id.id,
                "quantity": 1.0,
                "lot_id": lot.id,
                "location_id": supplier_location.id,
                "location_dest_id": stock_location.id,
            }
        )
        vals = move._prepare_vehicle_values(move_line)
        self.assertEqual(vals["name"], f"{product.name} ({lot.name})")
        self.assertEqual(vals["model_id"], self.vehicle_model.id)
        self.assertEqual(vals["product_id"], product.id)
        self.assertEqual(vals["stock_picking_id"], picking.id)
        self.assertEqual(vals["lot_id"], lot.id)
        self.assertEqual(vals["purchase_order_id"], self.purchase.id)
        self.assertEqual(vals["order_date"], self.purchase.date_order.date())
        self.assertEqual(vals["location"], stock_location.display_name)
        self.assertEqual(vals["net_car_value"], purchase_line.price_subtotal)

    def test_vehicle_creation_sets_purchase_fields_on_receipt(self):
        product = self.env["product.product"].create(
            {
                "name": "Receipt Vehicle Product",
                "type": "consu",
                "tracking": "serial",
                "tms_vehicle": True,
                "vehicle_type": "car",
                "model_id": self.vehicle_model.id,
            }
        )
        self.purchase.write({"date_order": "2024-07-15 12:00:00"})
        purchase_line = self.env["purchase.order.line"].create(
            {
                "order_id": self.purchase.id,
                "product_id": product.id,
                "product_qty": 1,
                "price_unit": 32000,
            }
        )
        lot = self.env["stock.lot"].create(
            {
                "name": "SN-RECEIPT-1",
                "product_id": product.id,
            }
        )
        supplier_location = self.env.ref("stock.stock_location_suppliers")
        stock_location = self.env.ref("stock.stock_location_stock")
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.env.ref("stock.picking_type_in").id,
                "location_id": supplier_location.id,
                "location_dest_id": stock_location.id,
            }
        )
        move = self.env["stock.move"].create(
            {
                "product_id": product.id,
                "product_uom": product.uom_id.id,
                "product_uom_qty": 1,
                "picking_id": picking.id,
                "location_id": supplier_location.id,
                "location_dest_id": stock_location.id,
                "purchase_line_id": purchase_line.id,
            }
        )
        self.env["stock.move.line"].create(
            {
                "move_id": move.id,
                "product_id": product.id,
                "product_uom_id": product.uom_id.id,
                "quantity": 1.0,
                "lot_id": lot.id,
                "location_id": supplier_location.id,
                "location_dest_id": stock_location.id,
            }
        )
        picking.button_validate()
        vehicle = lot.vehicle_id
        self.assertTrue(vehicle)
        self.assertEqual(vehicle.purchase_order_id, self.purchase)
        self.assertEqual(vehicle.order_date, self.purchase.date_order.date())
        self.assertEqual(vehicle.location, stock_location.display_name)
        self.assertEqual(vehicle.net_car_value, purchase_line.price_subtotal)
