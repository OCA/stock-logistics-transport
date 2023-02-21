# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.addons.shipment_advice_planner.tests.test_picking_can_be_planned import (
    TestPickingCanBePlanned as TestPickingCanBePlannedBase,
)

from .common import TestShipmentAdvicePlannerToursolverCommon


class TestPickingCanBePlanned(
    TestPickingCanBePlannedBase, TestShipmentAdvicePlannerToursolverCommon
):
    def test_01(self):
        picking = self.pickings.filtered(lambda p: p.state == "assigned")[0]
        self.assert_picking_can_be_planned_in_shipment_advice(picking)
        self._create_task()
        self.assertTrue(picking.toursolver_task_id)
        self.assert_can_not_be_planned_in_shipment_advice(picking)
        picking.toursolver_task_id.state = "done"
        self.assert_picking_can_be_planned_in_shipment_advice(picking)
        picking.toursolver_task_id.state = "cancelled"
        self.assert_picking_can_be_planned_in_shipment_advice(picking)
        picking.toursolver_task_id.state = "draft"
        self.assert_can_not_be_planned_in_shipment_advice(picking)
