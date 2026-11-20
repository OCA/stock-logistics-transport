from odoo import Command

from .common import Common


class TestShipmentAdvicePlan(Common):
    def test_onchange_shipment_type_with_delivery_and_receipt(self):
        delivery = self.move_product_out1.picking_id
        pickup = self.move_product_in1.picking_id
        pickings = delivery | pickup
        wizard = (
            self.env["wizard.plan.shipment"]
            .with_context(active_model="stock.picking", active_ids=pickings.ids)
            .create(
                {
                    "shipment_advice_id": self.shipment_advice_out.id,
                    "picking_ids": [Command.set(pickings.ids)],
                }
            )
        )
        wizard._onchange_shipment_advice_id()
        self.assertEqual(wizard.picking_ids, pickings)
        wizard.action_plan()
        self.assertEqual(self.shipment_advice_out.planned_picking_ids, pickings)
        wizard.shipment_advice_id = self.shipment_advice_in
        wizard._onchange_shipment_advice_id()
        self.assertEqual(wizard.picking_ids, pickup)

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
