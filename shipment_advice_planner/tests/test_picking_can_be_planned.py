# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from .common import TestShipmentAdvicePlannerCommon


class TestPickingCanBePlanned(TestShipmentAdvicePlannerCommon):
    def assert_picking_can_be_planned_in_shipment_advice(self, picking):
        self.assertTrue(picking)
        self.assertTrue(picking.can_be_planned_in_shipment_advice)
        self.assertFalse(
            self.env["stock.picking"].search(
                [
                    ("id", "=", picking.id),
                    ("can_be_planned_in_shipment_advice", "=", False),
                ]
            ),
        )
        self.assertEqual(
            self.env["stock.picking"].search(
                [
                    ("id", "=", picking.id),
                    ("can_be_planned_in_shipment_advice", "=", True),
                ]
            ),
            picking,
        )

    def assert_can_not_be_planned_in_shipment_advice(self, picking):
        self.assertTrue(picking)
        self.assertFalse(picking.can_be_planned_in_shipment_advice)
        self.assertFalse(
            self.env["stock.picking"].search(
                [
                    ("id", "=", picking.id),
                    ("can_be_planned_in_shipment_advice", "=", True),
                ]
            ),
        )
        self.assertEqual(
            self.env["stock.picking"].search(
                [
                    ("id", "=", picking.id),
                    ("can_be_planned_in_shipment_advice", "=", False),
                ]
            ),
            picking,
        )

    def test_00(self):
        non_assigned_picking = self.pickings.filtered(lambda p: p.state != "assigned")[
            0
        ]
        self.assert_can_not_be_planned_in_shipment_advice(non_assigned_picking)
        non_autgoing_picking = self.pickings.filtered(
            lambda p: p.picking_type_code != "outgoing"
        )[0]
        self.assert_can_not_be_planned_in_shipment_advice(non_autgoing_picking)
        picking = self.pickings.filtered(lambda p: p.state == "assigned")[0]
        self.assert_picking_can_be_planned_in_shipment_advice(picking)
        picking.planned_shipment_advice_id = self.env["shipment.advice"].create(
            {"shipment_type": "outgoing"}
        )
        self.assert_can_not_be_planned_in_shipment_advice(non_autgoing_picking)
