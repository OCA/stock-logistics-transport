# Copyright 2020 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from .common import TestShipmentAdvicePlannerToursolverCommon


class TestToursolverDeliveryWindow(TestShipmentAdvicePlannerToursolverCommon):
    def setUp(self):
        super().setUp()
        self.task = self._create_task()

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
