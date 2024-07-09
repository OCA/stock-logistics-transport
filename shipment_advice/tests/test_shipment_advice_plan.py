# Copyright 2021 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from .common import Common


class TestShipmentAdvicePlan(Common):
    def test_shipment_advice_plan_picking(self):
        picking = self.move_product_out1.picking_id
        wiz = self.plan_records_in_shipment(self.shipment_advice_out, picking)
        self.assertEqual(wiz.picking_ids, picking)
        self.assertFalse(wiz.move_ids)
        self.assertEqual(wiz.shipment_advice_id, self.shipment_advice_out)
        self.assertEqual(wiz.shipment_advice_id.planned_picking_ids, picking)
        self.assertEqual(wiz.shipment_advice_id.planned_pickings_count, 1)
        self.assertEqual(wiz.shipment_advice_id.planned_move_ids, picking.move_ids)
        self.assertEqual(wiz.shipment_advice_id.planned_moves_count, 3)

    def test_shipment_advice_plan_move(self):
        picking = self.move_product_out1.picking_id
        wiz = self.plan_records_in_shipment(
            self.shipment_advice_out, self.move_product_out1
        )
        self.assertEqual(wiz.move_ids, self.move_product_out1)
        self.assertFalse(wiz.picking_ids)
        self.assertEqual(wiz.shipment_advice_id, self.shipment_advice_out)
        self.assertEqual(wiz.shipment_advice_id.planned_picking_ids, picking)
        self.assertEqual(wiz.shipment_advice_id.planned_pickings_count, 1)
        self.assertEqual(
            wiz.shipment_advice_id.planned_move_ids, self.move_product_out1
        )
        self.assertEqual(wiz.shipment_advice_id.planned_moves_count, 1)
