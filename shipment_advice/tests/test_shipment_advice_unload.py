# Copyright 2021 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from .common import Common


class TestShipmentAdviceUnload(Common):
    def test_shipment_advice_unload_picking(self):
        self.progress_shipment_advice(self.shipment_advice_out)
        # Load picking
        picking = self.move_product_out1.picking_id
        self.load_records_in_shipment(self.shipment_advice_out, picking)
        self.assertEqual(self.shipment_advice_out.loaded_picking_ids, picking)
        self.assertEqual(
            self.shipment_advice_out.loaded_move_line_ids,
            self.move_product_out1.move_line_ids
            | self.move_product_out2.move_line_ids
            | self.move_product_out3.move_line_ids,
        )
        # Unload it
        self.unload_records_from_shipment(self.shipment_advice_out, picking)
        self.assertFalse(self.shipment_advice_out.loaded_picking_ids)
        self.assertFalse(self.shipment_advice_out.loaded_move_line_ids)

    def test_shipment_advice_unload_move_line(self):
        self.progress_shipment_advice(self.shipment_advice_out)
        # Load move line
        move_line = self.move_product_out1.move_line_ids
        self.load_records_in_shipment(self.shipment_advice_out, move_line)
        self.assertEqual(move_line.qty_done, 20)
        self.assertEqual(
            self.shipment_advice_out.loaded_move_line_without_package_ids, move_line
        )
        # Unload it
        self.unload_records_from_shipment(self.shipment_advice_out, move_line)
        self.assertFalse(move_line.qty_done)
        self.assertFalse(self.shipment_advice_out.loaded_move_line_without_package_ids)

    def test_shipment_advice_unload_package_level(self):
        self.progress_shipment_advice(self.shipment_advice_out)
        # Load package level
        package_level = self.move_product_out2.move_line_ids.package_level_id
        self.load_records_in_shipment(self.shipment_advice_out, package_level)
        self.assertTrue(package_level.is_done)
        self.assertEqual(self.move_product_out2.move_line_ids.qty_done, 10)
        self.assertEqual(self.move_product_out3.move_line_ids.qty_done, 10)
        self.assertFalse(self.shipment_advice_out.loaded_move_line_without_package_ids)
        self.assertEqual(
            self.shipment_advice_out.loaded_package_ids, package_level.package_id
        )
        # Unload it
        package_level._unload_from_shipment()
        self.assertFalse(package_level.is_done)
        self.assertFalse(self.move_product_out2.move_line_ids.qty_done)
        self.assertFalse(self.move_product_out3.move_line_ids.qty_done)
        self.assertFalse(self.shipment_advice_out.loaded_package_ids)
