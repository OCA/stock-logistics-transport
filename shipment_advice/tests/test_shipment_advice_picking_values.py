# Copyright 2024 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from .common import Common


class TestShipmentPickingValues(Common):
    def test_picking_loaded_waiting_quantity_no(self):
        move = self.move_product_out1
        picking = move.picking_id
        self.load_records_in_shipment(self.shipment_advice_out, picking)
        self.assertEqual(picking.loaded_waiting_quantity, 0)

    def test_picking_loaded_waiting_quantity_yes(self):
        move = self.move_product_out1
        picking = move.picking_id
        quantity = move.product_qty
        move.move_line_ids.reserved_uom_qty = quantity - 3
        self.load_records_in_shipment(self.shipment_advice_out, picking)
        self.assertEqual(picking.loaded_waiting_quantity, 3)
