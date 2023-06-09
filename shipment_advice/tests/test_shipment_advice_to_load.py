# Copyright 2023 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)


from .common import Common


class TestShipmentAdviceToLoad(Common):
    def test_shipment_advice_not_planned_lines_to_load(self):
        self.progress_shipment_advice(self.shipment_advice_out)
        # Load a transfer partially
        self.load_records_in_shipment(
            self.shipment_advice_out, self.move_product_out1.move_line_ids
        )
        self.assertEqual(
            self.move_product_out1.move_line_ids.shipment_advice_id,
            self.shipment_advice_out,
        )
        # Check the lines computed by the shipment advice that could be loaded
        lines_to_load = (
            self.move_product_out2.move_line_ids | self.move_product_out3.move_line_ids
        )
        self.assertFalse(lines_to_load.shipment_advice_id)
        self.assertEqual(self.shipment_advice_out.line_to_load_ids, lines_to_load)

    def test_shipment_advice_planned_lines_to_load(self):
        self.progress_shipment_advice(self.shipment_advice_out)
        # Plan a transfer in the shipment advice
        picking = self.move_product_out2.picking_id
        self.plan_records_in_shipment(self.shipment_advice_out, picking)
        # Check the lines computed by the shipment advice that could be loaded
        # (= all the lines of the planned transfer)
        lines_to_load = picking.move_line_ids
        self.assertFalse(lines_to_load.shipment_advice_id)
        self.assertEqual(self.shipment_advice_out.line_to_load_ids, lines_to_load)
        # Load some goods from the planned transfer
        self.load_records_in_shipment(
            self.shipment_advice_out, self.move_product_out1.move_line_ids
        )
        self.assertEqual(
            self.move_product_out1.move_line_ids.shipment_advice_id,
            self.shipment_advice_out,
        )
        # Check the lines computed by the shipment advice that could be loaded
        # (= the remaining planned lines of the transfer not yet loaded)
        self.shipment_advice_out.invalidate_recordset()
        lines_to_load2 = (
            self.move_product_out2.move_line_ids | self.move_product_out3.move_line_ids
        )
        self.assertFalse(lines_to_load2.shipment_advice_id)
        self.assertEqual(self.shipment_advice_out.line_to_load_ids, lines_to_load2)
