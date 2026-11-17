# Copyright 2026 ACSONE SA/NV (https://www.acsone.eu)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from .common import ShipmentAdviceSearchCommonCase


class TestShipmentAdviceStockPicking(ShipmentAdviceSearchCommonCase):
    def test_search_order_by_shipment_sequence(self):
        domain = [("id", "in", (self.picking1 | self.picking2 | self.picking3).ids)]
        order = "sequence_in_shipment_advice, id"
        self.pickings = self.env["stock.picking"].with_context(
            active_shipment_advice_id=self.shipment_advice_out.id
        )
        self.assertEqual(
            self.pickings.search(domain, order=order).ids,
            [self.picking2.id, self.picking1.id, self.picking3.id],
        )
        self.assertEqual(
            self.pickings.search(domain, order=order, limit=1).ids, self.picking2.ids
        )
        self.assertEqual(
            self.pickings.search(domain, order=order, limit=1, offset=1).ids,
            self.picking1.ids,
        )
        self.assertEqual(
            self.pickings.search(
                domain, order="sequence_in_shipment_advice desc, id"
            ).ids,
            [self.picking1.id, self.picking2.id, self.picking3.id],
        )
        self.assertEqual(
            self.pickings.search(
                domain, order="id desc, sequence_in_shipment_advice"
            ).ids,
            [self.picking3.id, self.picking2.id, self.picking1.id],
        )
        self.assertEqual(
            self.pickings.search(domain, order="id desc").ids,
            [self.picking3.id, self.picking2.id, self.picking1.id],
        )
        self.assertEqual(
            self.pickings.with_context(active_shipment_advice_id=False)
            .search(domain, order="id desc")
            .ids,
            [self.picking3.id, self.picking2.id, self.picking1.id],
        )
        self.assertEqual(self.pickings.search_count(domain), 3)

        self.planned_orders[0].sequence = 1
        self.assertEqual(
            self.pickings.search(domain, order=order).ids,
            [self.picking1.id, self.picking2.id, self.picking3.id],
        )
