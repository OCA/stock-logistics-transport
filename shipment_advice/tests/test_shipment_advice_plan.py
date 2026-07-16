# Copyright 2021 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from .common import Common


class TestShipmentAdvicePlan(Common):
    def _create_distinct_picking(self, picking_type, product, qty):
        group2 = self.env["procurement.group"].create({})
        return self._create_move(picking_type, product, qty, group2).picking_id

    def test_shipment_advice_plan_picking(self):
        picking = self.move_product_out1.picking_id

        self.assertFalse(self.shipment_advice_out.planned_picking_order_ids)
        wiz = self.plan_records_in_shipment(self.shipment_advice_out, picking)
        self.assertEqual(wiz.picking_ids, picking)
        self.assertFalse(wiz.move_ids)
        self.assertEqual(wiz.shipment_advice_id, self.shipment_advice_out)
        self.assertEqual(wiz.shipment_advice_id.planned_picking_ids, picking)
        self.assertEqual(wiz.shipment_advice_id.planned_pickings_count, 1)
        self.assertEqual(wiz.shipment_advice_id.planned_move_ids, picking.move_ids)
        self.assertEqual(wiz.shipment_advice_id.planned_moves_count, 3)

        # test generation of default order for pickings
        picking2 = self._create_distinct_picking(
            self.picking_type_out, self.product_out2, 5
        )
        self.plan_records_in_shipment(self.shipment_advice_out, picking2)
        self.assertTrue(self.shipment_advice_out.planned_picking_order_ids)

        # test that manual changes to order are preserved
        picking.with_context(
            active_shipment_advice_id=self.shipment_advice_out.id
        ).sequence_in_shipment_advice = 20
        picking2.with_context(
            active_shipment_advice_id=self.shipment_advice_out.id
        ).sequence_in_shipment_advice = 0

        shipment_advice_out_first_picking = (
            self.env["stock.picking"]
            .with_context(active_shipment_advice_id=self.shipment_advice_out.id)
            .search(
                [("move_ids.shipment_advice_id", "=", self.shipment_advice_out.id)],
            )
        )
        self.assertEqual(shipment_advice_out_first_picking[0], picking2)

        # test stock.picking search count don't raise error
        self.env["stock.picking"].with_context(
            active_shipment_advice_id=self.shipment_advice_out.id
        ).search_count(
            [("move_ids.shipment_advice_id", "=", self.shipment_advice_out.id)]
        )

        # test the same is reflected when searching at stock.move level
        shipment_advice_out_first_move = (
            self.env["stock.move"]
            .with_context(active_shipment_advice_id=self.shipment_advice_out.id)
            .search(
                [("shipment_advice_id", "=", self.shipment_advice_out.id)],
            )
        )

        self.assertEqual(shipment_advice_out_first_move.picking_id[0], picking2)

        # test stock.move search count don't raise error
        self.env["stock.move"].with_context(
            active_shipment_advice_id=self.shipment_advice_out.id
        ).search_count([("shipment_advice_id", "=", self.shipment_advice_out.id)])

        # test same picking planned in different shipment advices might have different
        # order
        shipment_advice_out2 = self.env["shipment.advice"].create(
            {"shipment_type": "outgoing"}
        )
        self.plan_records_in_shipment(shipment_advice_out2, picking)
        self.assertTrue(
            picking.with_context(
                active_shipment_advice_id=self.shipment_advice_out.id
            ).sequence_in_shipment_advice
            != picking.with_context(
                active_shipment_advice_id=shipment_advice_out2.id
            ).sequence_in_shipment_advice
        )

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

    def test_shipment_advice_plan_picking_order_sorted(self):
        """Verify that planned_picking_ids sorted by sequence_in_shipment_advice
        (as done in qweb templates) respects the user-defined order."""
        picking1 = self.move_product_out1.picking_id
        picking2 = self._create_distinct_picking(
            self.picking_type_out, self.product_out2, 5
        )

        self.plan_records_in_shipment(self.shipment_advice_out, picking1)
        self.plan_records_in_shipment(self.shipment_advice_out, picking2)

        picking2.with_context(
            active_shipment_advice_id=self.shipment_advice_out.id
        ).sequence_in_shipment_advice = 0
        picking1.with_context(
            active_shipment_advice_id=self.shipment_advice_out.id
        ).sequence_in_shipment_advice = 10

        sa = self.shipment_advice_out
        sorted_pickings = sa.planned_picking_ids.sorted(
            lambda p: p.with_context(
                active_shipment_advice_id=sa.id
            ).sequence_in_shipment_advice
        )

        self.assertEqual(sorted_pickings[0], picking2)
        self.assertEqual(sorted_pickings[1], picking1)
