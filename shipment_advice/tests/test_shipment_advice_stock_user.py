# Copyright 2021 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from .common import Common


class TestShipmentAdviceStockUser(Common):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.setUpClassUsers()

    def test_shipment_advice_button_open_planned_pickings(self):
        shipment_advice = self.shipment_advice_out.with_user(self.stock_user)
        action = shipment_advice.button_open_planned_pickings()
        self.assertEqual(action["name"], "Transfers")

    def test_shipment_advice_button_open_planned_moves(self):
        shipment_advice = self.shipment_advice_out.with_user(self.stock_user)
        action = shipment_advice.button_open_planned_moves()
        self.assertEqual(action["name"], "Stock Moves")

    def test_shipment_advice_button_open_loaded_pickings(self):
        shipment_advice = self.shipment_advice_out.with_user(self.stock_user)
        action = shipment_advice.button_open_loaded_pickings()
        self.assertEqual(action["name"], "Transfers")

    def test_shipment_advice_button_open_loaded_move_lines(self):
        shipment_advice = self.shipment_advice_out.with_user(self.stock_user)
        action = shipment_advice.button_open_loaded_move_lines()
        self.assertEqual(action["name"], "Moves History")

    def test_shipment_advice_button_open_loaded_packages(self):
        shipment_advice = self.shipment_advice_out.with_user(self.stock_user)
        action = shipment_advice.button_open_loaded_packages()
        self.assertEqual(action["name"], "Packages")

    def test_shipment_advice_button_open_deliveries_in_progress(self):
        shipment_advice = self.shipment_advice_out.with_user(self.stock_user)
        action = shipment_advice.button_open_deliveries_in_progress()
        self.assertEqual(action["name"], "Transfers")

    def test_shipment_advice_button_open_receptions_in_progress(self):
        shipment_advice = self.shipment_advice_in.with_user(self.stock_user)
        action = shipment_advice.button_open_receptions_in_progress()
        self.assertEqual(action["name"], "Transfers")

    def test_stock_move_line_button_load_in_shipment(self):
        move_line = self.move_product_out1.move_line_ids[0]
        action = move_line.with_user(self.stock_user).button_load_in_shipment()
        self.assertEqual(action["name"], "Load in shipment")

    def test_stock_move_line_button_load_in_shipment_different_pack(self):
        move_lines = self.move_product_out1.move_line_ids
        action = move_lines.with_user(self.stock_user).button_load_in_shipment()
        self.assertEqual(action["name"], "Load in shipment")

    def test_stock_picking_button_load_in_shipment(self):
        move_line = self.move_product_out1.move_line_ids[0]
        picking = move_line.picking_id.with_user(self.stock_user)
        action = picking.button_load_in_shipment()
        self.assertEqual(action["name"], "Load in shipment")

    def test_stock_picking_button_plan_in_shipment(self):
        move_line = self.move_product_out1.move_line_ids[0]
        picking = move_line.picking_id.with_user(self.stock_user)
        action = picking.button_plan_in_shipment()
        self.assertEqual(action["name"], "Plan in shipment")

    def test_stock_picking_button_unload_from_shipment(self):
        move_line = self.move_product_out1.move_line_ids[0]
        picking = move_line.picking_id.with_user(self.stock_user)
        action = picking.button_unload_from_shipment()
        self.assertEqual(action["name"], "Unload in shipment")

    def test_stock_package_level_button_load_in_shipment(self):
        package_level = self.move_product_out1.package_level_id
        action = package_level.with_user(self.stock_user).button_load_in_shipment()
        self.assertEqual(action["name"], "Load in shipment")

    def test_wizard_plan_and_load_shipment(self):
        move = self.move_product_out1
        self.plan_records_in_shipment(
            self.shipment_advice_out,
            move,
            user=self.stock_user,
        )
        self.progress_shipment_advice(self.shipment_advice_out)
        wiz = self.load_records_in_shipment(
            self.shipment_advice_out,
            move.move_line_ids,
            user=self.stock_user,
        )
        self.assertFalse(wiz.picking_ids)
