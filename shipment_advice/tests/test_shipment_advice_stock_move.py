# Copyright 2026 ACSONE SA/NV (https://www.acsone.eu)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from .common import ShipmentAdviceSearchCommonCase


class TestShipmentAdviceStockPicking(ShipmentAdviceSearchCommonCase):
    def test_search_order_by_shipment_sequence(self):
        # picking 3 should always be last since it's not linked to the active shipment advice
        moves = self.picking1.move_ids | self.picking2.move_ids | self.picking3.move_ids

        results = (
            self.env["stock.move"]
            .with_context(active_shipment_advice_id=self.shipment_advice_out.id)
            .search(
                [("id", "in", moves.ids)],
                order="picking_sequence_in_shipment_advice, id",
            )
        )
        self.assertEqual(
            results.ids,
            [
                *self.picking2.move_ids.ids,
                *self.picking1.move_ids.ids,
                *self.picking3.move_ids.ids,
            ],
        )

        results = (
            self.env["stock.move"]
            .with_context(active_shipment_advice_id=self.shipment_advice_out.id)
            .search(
                [("id", "in", moves.ids)],
                order="picking_sequence_in_shipment_advice desc, id",
            )
        )
        self.assertEqual(
            results.ids,
            [
                *self.picking1.move_ids.ids,
                *self.picking2.move_ids.ids,
                *self.picking3.move_ids.ids,
            ],
        )
