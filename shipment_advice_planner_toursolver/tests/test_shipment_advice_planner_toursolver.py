# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from freezegun import freeze_time
from vcr_unittest import VCRTestCase

from odoo.exceptions import UserError
from odoo.tools import mute_logger

from .common import TestShipmentAdvicePlannerToursolverCommon


class TestShipmentAdvicePlannerToursolver(
    VCRTestCase, TestShipmentAdvicePlannerToursolverCommon
):
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
        planned_picking = shipment.planned_picking_ids
        planned_partners = shipment.planned_picking_ids.mapped("partner_id")
        self.assertEqual(
            set(planned_picking.mapped("toursolver_shipment_advice_rank")),
            {1, 2},
        )
        first_stop = planned_picking.filtered(
            lambda p: p.toursolver_shipment_advice_rank == 1
        ).partner_id
        second_stop = planned_picking.filtered(
            lambda p: p.toursolver_shipment_advice_rank == 2
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
            "The following partners are not found into the optimization result: Oscar Morgan",
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
