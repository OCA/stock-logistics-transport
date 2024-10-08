# Copyright 2020 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from .common import TestShipmentAdvicePlannerToursolverCommon


class TestToursolverDeliveryWindow(TestShipmentAdvicePlannerToursolverCommon):
    def setUp(self):
        super().setUp()
        self.task = self._create_task()
        self.backend = self.task.toursolver_backend_id

    def test_rqst_options_properties(self):
        rqst = self.task._toursolver_post_json_request()
        options = rqst["options"]
        self.assertEqual(options["vehicleCode"], "deliveryIntermediateVehicle")
        self.assertFalse(options["useForbiddenTransitAreas"])

    def test_rqst_orders_properties(self):
        rqst = self.task._toursolver_post_json_request()
        orders = rqst["orders"]
        for order in orders:
            self.assertEqual(order["maxDelayTime"], "00:40")
            self.assertEqual(order["delayPenaltyPerHour"], 20)

    def test_default_delivery_windows(self):
        self.backend.partner_default_delivery_window_start = False
        self.backend.partner_default_delivery_window_end = False
        rqst = self.task._toursolver_post_json_request()
        orders = rqst["orders"]
        for order in orders:
            self.assertNotIn("timeWindows", order)

        self.backend.partner_default_delivery_window_start = 8.0
        self.backend.partner_default_delivery_window_end = 17.0
        rqst = self.task._toursolver_post_json_request()
        orders = rqst["orders"]
        for order in orders:
            self.assertEqual(
                order["timeWindows"], [{"beginTime": "08:00", "endTime": "17:00"}]
            )

        self.backend.delivery_window_disabled = True
        rqst = self.task._toursolver_post_json_request()
        orders = rqst["orders"]
        for order in orders:
            self.assertNotIn("timeWindows", order)
