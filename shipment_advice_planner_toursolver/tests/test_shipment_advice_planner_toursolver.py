# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import json
from unittest.mock import patch

from freezegun import freeze_time
from vcr_unittest import VCRTestCase

from odoo import Command
from odoo.exceptions import UserError
from odoo.tools import mute_logger

from .common import TestShipmentAdvicePlannerToursolverCommon


class TestShipmentAdvicePlannerToursolver(
    VCRTestCase, TestShipmentAdvicePlannerToursolverCommon
):
    def test_wizard_plans_delivery_and_pickup_in_one_tour(self):
        delivery = self.pickings.filtered(
            lambda picking: (
                picking.picking_type_code == "outgoing"
                and picking.state == "assigned"
                and picking.picking_type_id.warehouse_id == self.warehouse
            )
        )[:1]
        self.assertTrue(delivery)
        picking_type = self.warehouse.in_type_id
        pickup = self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "location_id": self.env.ref("stock.stock_location_customers").id,
                "location_dest_id": picking_type.default_location_dest_id.id,
                "partner_id": delivery.partner_id.id,
            }
        )
        product = delivery.move_ids[0].product_id
        self.env["stock.move"].create(
            {
                "name": product.name,
                "product_id": product.id,
                "product_uom": product.uom_id.id,
                "product_uom_qty": 1,
                "picking_id": pickup.id,
                "location_id": pickup.location_id.id,
                "location_dest_id": pickup.location_dest_id.id,
            }
        )
        pickup.action_confirm()
        pickup.action_assign()
        self.assertEqual(pickup.state, "assigned")
        pickings = delivery | pickup
        wizard = (
            self.env["shipment.advice.planner"]
            .with_context(active_model="stock.picking", active_ids=pickings.ids)
            .create(
                {
                    "warehouse_id": self.warehouse.id,
                    "shipment_planning_method": "toursolver",
                    "toursolver_force_delivery_first": True,
                    "delivery_resource_ids": [Command.set(self.resource_1.ids)],
                }
            )
        )
        self.assertEqual(wizard.picking_to_plan_ids, pickings)
        wizard.button_plan_shipments()
        task = pickings.toursolver_task_id
        self.assertEqual(len(task), 1)
        self.assertEqual(task.picking_ids, pickings)
        self.assertTrue(task.force_delivery_first)
        request = task._toursolver_post_json_request()
        order_types = {order["id"]: order["type"] for order in request["orders"]}
        delivery_id = f"{delivery.partner_id.id}_delivery"
        pickup_id = f"{pickup.partner_id.id}_pickup"
        self.assertEqual(order_types, {delivery_id: 2, pickup_id: 1})
        resource_id = self.resource_1.resource_id
        result = {
            "status": "OK",
            "tours": [
                {
                    "resourceId": resource_id,
                    "plannedOrders": [
                        {"stopType": 1, "stopStartTime": "08:00", "dayId": "1"},
                        {
                            "resourceId": resource_id,
                            "stopId": delivery_id,
                            "stopType": 0,
                        },
                        {"resourceId": resource_id, "stopId": pickup_id, "stopType": 0},
                        {"stopType": 2, "stopStartTime": "09:00", "dayId": "1"},
                    ],
                    "deliveryCost": 0,
                    "additionalCost": 0,
                    "totalCost": 0,
                    "travelDistance": 0,
                    "travelDuration": "00:00",
                }
            ],
        }
        task.request_data = base64.b64encode(json.dumps(request).encode())
        task.toursolver_status = "terminated"
        with patch.object(type(task), "_toursolver_get", return_value=result):
            task.button_get_result()
        self.assertEqual(task.state, "done")
        shipment = task.shipment_advice_ids
        self.assertEqual(len(shipment), 1)
        self.assertEqual(shipment.shipment_type, "outgoing")
        self.assertEqual(shipment.planned_picking_ids, pickings)
        sequences = {
            order.operation_type: order.sequence
            for order in shipment.planned_partner_order_ids
        }
        self.assertEqual(sequences, {"delivery": 1, "pickup": 2})

    def test_query_url(self):
        expected_query_url = (
            "https://geoservices.geoconcept.com/ToursolverCloud/api/ts/toursolver/"
            "test?param1=param_1&param2=param_2&tsCloudApiKey=fake_api_key"
        )
        task = self._create_task()
        query_url = task._toursolver_query_url(
            action="test", param1="param_1", param2="param_2"
        )
        self.assertEqual(query_url, expected_query_url)

    def test_toursolver_task_creation(self):
        self.wizard_form.shipment_planning_method = "toursolver"
        wizard = self.wizard_form.save()
        self.assertFalse(wizard.picking_to_plan_ids.toursolver_task_id)
        wizard.button_plan_shipments()
        task = wizard.picking_to_plan_ids.toursolver_task_id
        self.assertTrue(task)
        self.assertEqual(len(wizard.picking_to_plan_ids), 9)
        self.assertEqual(len(task.picking_ids), 9)

    @mute_logger("TourSolver Connexion")
    def test_task_send_request_fail_connexion(self):
        task = self._create_task()
        task.button_send_request()
        self.assertEqual(task.state, "error")
        self.assertIn("403 Client Error", task.toursolver_error_message)

    @mute_logger("TourSolver Connexion")
    def test_task_send_request_no_order(self):
        task = self._create_task()
        task.picking_ids = False
        task.button_send_request()
        self.assertEqual(task.state, "error")
        self.assertEqual(task.toursolver_error_message, "no orders found")

    def test_orders_are_split_by_operation_type(self):
        task = self._create_task()
        deliveries = task.picking_ids.filtered(
            lambda picking: picking.picking_type_id.code == "outgoing"
        )[:2]
        pickup = self.env["stock.picking"].search(
            [
                ("picking_type_id.code", "=", "incoming"),
                ("partner_id", "!=", False),
            ],
            limit=1,
        )
        self.assertEqual(len(deliveries), 2)
        self.assertTrue(pickup)

        partner = self.env["res.partner"].create({"name": "Multi-operation customer"})
        deliveries.partner_id = partner
        pickup.partner_id = partner
        task.picking_ids = deliveries | pickup

        orders = task._toursolver_json_request_orders()
        self.assertEqual(len(orders), 2)
        order_by_type = {order["type"]: order for order in orders}
        self.assertEqual(set(order_by_type), {0, 1})
        self.assertEqual(order_by_type[0]["id"], f"{partner.id}_delivery")
        self.assertEqual(order_by_type[1]["id"], f"{partner.id}_pickup")
        self.assertEqual(
            order_by_type[0]["customDataMap"]["pickingIds"],
            str(deliveries.ids),
        )
        self.assertEqual(
            order_by_type[1]["customDataMap"]["pickingIds"],
            f"[{pickup.id}]",
        )

    def _check_mixed_shipment_planning(self, same_partner, force_delivery_first):
        task = self._create_task()
        deliveries = task.picking_ids.filtered(
            lambda picking: picking.picking_type_id.code == "outgoing"
        )[:2]
        pickup = self.env["stock.picking"].search(
            [
                ("picking_type_id.code", "=", "incoming"),
                ("move_ids", "!=", False),
            ],
            limit=1,
        )
        self.assertEqual(len(deliveries), 2)
        self.assertTrue(pickup)

        delivery_partner = self.env["res.partner"].create({"name": "Delivery partner"})
        pickup_partner = (
            delivery_partner
            if same_partner
            else self.env["res.partner"].create({"name": "Pickup partner"})
        )
        deliveries.partner_id = delivery_partner
        pickup.partner_id = pickup_partner
        pickings = deliveries | pickup
        task.picking_ids = pickings
        task.force_delivery_first = force_delivery_first

        shipment = self.env["shipment.advice"].create(
            {
                "shipment_type": "outgoing",
                "warehouse_id": self.warehouse.id,
                "toursolver_task_id": task.id,
                "toursolver_resource_id": self.resource_1.id,
                "planned_move_ids": [Command.set(pickings.move_ids.ids)],
            }
        )
        request = task._toursolver_post_json_request()
        orders = {order["id"]: order for order in request["orders"]}
        delivery_id = f"{delivery_partner.id}_delivery"
        pickup_id = f"{pickup_partner.id}_pickup"
        self.assertEqual(set(orders), {delivery_id, pickup_id})
        self.assertEqual(orders[delivery_id]["type"], 2 if force_delivery_first else 0)
        self.assertEqual(orders[pickup_id]["type"], 1)
        self.assertEqual(
            set(json.loads(orders[delivery_id]["customDataMap"]["pickingIds"])),
            set(deliveries.ids),
        )
        self.assertEqual(
            json.loads(orders[pickup_id]["customDataMap"]["pickingIds"]),
            pickup.ids,
        )
        task._toursolver_send_request()
        task._toursolver_get_result()
        planned_orders = shipment.planned_partner_order_ids
        self.assertEqual(len(planned_orders), 2)
        for partner, operation_type, expected_pickings in (
            (delivery_partner, "delivery", deliveries),
            (pickup_partner, "pickup", pickup),
        ):
            planned = planned_orders.filtered(
                lambda order, p=partner, op=operation_type: (
                    order.partner_id == p and order.operation_type == op
                )
            )
            self.assertEqual(len(planned), 1)
            self.assertEqual(planned.stock_picking_ids, expected_pickings)

    def test_mixed_shipment_same_partner(self):
        self._check_mixed_shipment_planning(
            same_partner=True, force_delivery_first=False
        )

    def test_mixed_shipment_different_partners(self):
        self._check_mixed_shipment_planning(
            same_partner=False, force_delivery_first=False
        )

    def test_mixed_shipment_force_delivery_first(self):
        self._check_mixed_shipment_planning(
            same_partner=True, force_delivery_first=True
        )

    def test_mixed_shipment_different_partners_force_delivery_first(self):
        self._check_mixed_shipment_planning(
            same_partner=False, force_delivery_first=True
        )

    def test_force_delivery_first_is_copied_to_task(self):
        self.wizard_form.shipment_planning_method = "toursolver"
        self.wizard_form.toursolver_force_delivery_first = True
        wizard = self.wizard_form.save()
        wizard.button_plan_shipments()
        task = wizard.picking_to_plan_ids.toursolver_task_id
        self.assertTrue(task)
        self.assertTrue(task.force_delivery_first)

    def test_task_send_request_ok_without_resources(self):
        task = self._create_task()
        task.button_send_request()
        self.assertEqual(task.state, "in_progress")
        self.assertFalse(task.toursolver_error_message)
        self.assertEqual(task.task_id, "7FFFFE79952E95FD4ZD-9FWZQBuyh4qWhv2qpg")

    def test_send_ok_with_resources(self):
        task = self._create_task()
        task.button_send_request()
        self.assertEqual(task.state, "in_progress")
        self.assertFalse(task.toursolver_error_message)
        self.assertEqual(task.task_id, "7FFFFE79952E95FD4ZD-9FWZQBuyh4qWhv2qpg")

    @freeze_time("2023-02-15 10:30:00")
    def test_resource_properties(self):
        self.assertDictEqual(
            self.resource_1.with_context(
                tz="Europe/Brussels"
            )._get_resource_properties(),
            {
                "globalCapacity": 9999,
                "id": "D1",
                "loadBeforeDeparture": True,
                "mobileLogin": "d1@email.com",
                "noReload": True,
                "openStart": False,
                "useAllCapacities": False,
                "workPenalty": 0.0,
                "workStartTime": "11:30:00",
                "travelPenalty": 0.0,
                "fixedLoadingDuration": "00:00:00",
            },
        )

    def test_check_status(self):
        task = self._create_task()
        task.button_send_request()
        self.assertEqual(task.state, "in_progress")
        self.assertFalse(task.toursolver_error_message)
        task.button_check_status()
        self.assertEqual(task.state, "success")

    def test_get_result_ok(self):
        task = self._create_task()
        task.button_send_request()
        self.assertEqual(task.state, "in_progress")
        self.assertFalse(task.toursolver_error_message)
        task.button_check_status()
        self.assertEqual(task.state, "success")
        task.button_get_result()
        self.assertEqual(task.state, "done")
        shipment = task.shipment_advice_ids
        self.assertEqual(shipment.toursolver_resource_id, self.resource_2)
        planned_partner_order = shipment.planned_partner_order_ids
        planned_partners = shipment.planned_picking_ids.mapped("partner_id")
        self.assertEqual(
            set(planned_partner_order.mapped("sequence")),
            {1, 2},
        )
        first_stop = planned_partner_order.filtered(
            lambda p: p.sequence == 1
        ).partner_id
        second_stop = planned_partner_order.filtered(
            lambda p: p.sequence == 2
        ).partner_id
        self.assertEqual(first_stop, planned_partners[1])
        self.assertEqual(second_stop, planned_partners[0])
        self.assertEqual(shipment.toursolver_nbr_tours, 1)
        self.assertEqual(shipment.toursolver_nbr_visits, 2)
        self.assertEqual(shipment.toursolver_delivery_cost, 12345.0)
        self.assertEqual(shipment.toursolver_additional_cost, 12345.0)
        self.assertEqual(shipment.toursolver_total_cost, 12345.0)
        self.assertEqual(shipment.toursolver_travel_distance, 12.345)
        self.assertEqual(shipment.toursolver_travel_duration, 5.5)
        self.assertEqual(
            shipment.toursolver_travel_start_dt,
            shipment._stop_start_time_to_dt("17:07", "1"),
        )
        self.assertEqual(
            shipment.toursolver_travel_end_dt,
            shipment._stop_start_time_to_dt("17:13", "1"),
        )
        self.assertEqual(shipment.toursolver_travel_total_time, 6.0 / 60)

    def test_get_result_ko(self):
        task = self._create_task()
        task.button_send_request()
        self.assertEqual(task.state, "in_progress")
        task.button_check_status()
        self.assertEqual(task.state, "success")
        task.button_get_result()
        self.assertEqual(task.toursolver_status, "failed")
        self.assertEqual(task.state, "error")
        self.assertEqual(
            task.toursolver_error_message,
            "The following operations are not found into the optimization result: "
            "Gemini Furniture, Oscar Morgan (delivery)",
        )
        self.assertFalse(task.shipment_advice_ids)

    def test_cron_sync_task(self):
        task = self._create_task()
        self.env[task._name]._cron_sync_task()
        self.assertEqual(task.state, "in_progress")
        self.env[task._name]._cron_sync_task()
        self.assertEqual(task.state, "done")
        self.assertEqual(
            task.shipment_advice_ids.toursolver_resource_id, self.resource_2
        )

    def test_backend_definition_creation(self):
        backend = self.env["toursolver.backend"].create({"name": "backend"})
        self.assertTrue(backend.definition_id)

    def test_recreate_task(self):
        """
        Recreate toursolver task

        It may happen that the shipment advice is created after the toursolver task is
        completed, and the user decides to add a picking to it.
        It's easier to have an action on the shipment advice to recreate the toursolver
        task without going through the planner again.

        As a safeguard, we do not allow this action unless the previous task has been
        removed. When the task is recreated, the new task will not generate a new
        shipment advice but will be assigned to the existing one.
        """
        task = self._create_task()
        task.button_send_request()
        self.assertEqual(task.state, "in_progress")
        self.assertFalse(task.toursolver_error_message)
        task.button_check_status()
        self.assertEqual(task.state, "success")
        task.button_get_result()
        self.assertEqual(task.state, "done")
        shipment = task.shipment_advice_ids
        self.assertEqual(shipment.state, "confirmed")
        self.assertFalse(shipment.is_create_toursolver_task_allowed)
        with self.assertRaises(
            UserError, msg="You can't recreate the toursolver task."
        ):
            shipment.create_toursolver_task()
        task.unlink()
        self.assertTrue(shipment.is_create_toursolver_task_allowed)
        shipment.create_toursolver_task()
        self.assertTrue(shipment.toursolver_task_id)
        task = shipment.toursolver_task_id
        self.assertEqual(task.state, "draft")
        task.button_send_request()
        self.assertEqual(task.state, "in_progress")
        self.assertFalse(task.toursolver_error_message)
        task.button_check_status()
        self.assertEqual(task.state, "success")
        task.button_get_result()
        self.assertEqual(task.state, "done")
        self.assertEqual(task.shipment_advice_ids, shipment)
        self.assertEqual(shipment.state, "confirmed")
