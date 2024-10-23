# Copyright 2021 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import fields
from odoo.exceptions import UserError

from .common import Common


class TestShipmentAdvice(Common):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_shipment_advice_confirm(self):
        self._check_sequence(self.shipment_advice_out)
        with self.assertRaises(UserError):
            self.shipment_advice_out.action_confirm()
        self.shipment_advice_out.arrival_date = fields.Datetime.now()
        self.shipment_advice_out.action_confirm()
        # Check 2nd user error, which is thrown if state is not equal to draft
        self.assertEqual(self.shipment_advice_out.state, "confirmed")
        with self.assertRaises(UserError):
            self.shipment_advice_out.action_confirm()

    def test_shipment_advice_in_progress(self):
        self.confirm_shipment_advice(self.shipment_advice_out)
        with self.assertRaises(UserError):
            self.shipment_advice_out.action_in_progress()
        self.shipment_advice_out.dock_id = self.dock
        self.shipment_advice_out.action_in_progress()
        self.assertEqual(self.shipment_advice_out.state, "in_progress")
        with self.assertRaises(UserError):
            self.shipment_advice_out.action_in_progress()

    def test_shipment_advice_incoming_done_full(self):
        """Validating an incoming shipment validates automatically planned
        transfers. Here the planned transfers have been fully received.
        """
        picking = self.move_product_in1.picking_id
        with self.assertRaises(UserError):
            self.shipment_advice_in.action_done()
        self._check_sequence(self.shipment_advice_in)
        self.plan_records_in_shipment(self.shipment_advice_in, picking)
        self.progress_shipment_advice(self.shipment_advice_in)
        for ml in picking.move_line_ids:
            ml.qty_done = ml.reserved_uom_qty
        picking._action_done()
        self.shipment_advice_in.action_done()
        self.assertEqual(self.shipment_advice_in.state, "done")
        self.assertTrue(
            all(
                move.state == "done"
                for move in self.shipment_advice_in.planned_move_ids
            )
        )
        self.assertEqual(picking.state, "done")

    def test_shipment_advice_incoming_done_partial(self):
        """Validating an incoming shipment validates automatically planned
        transfers. Here the planned transfers have been partially received.
        """
        picking = self.move_product_in1.picking_id
        # Plan a move
        self.plan_records_in_shipment(self.shipment_advice_in, self.move_product_in1)
        self.progress_shipment_advice(self.shipment_advice_in)
        # Receive it (making its related transfer partially received)
        for ml in self.move_product_in1.move_line_ids:
            ml.qty_done = ml.reserved_uom_qty
        self.assertEqual(picking, self.move_product_in2.picking_id)
        # When validating the shipment, a backorder is created for unprocessed moves
        self.shipment_advice_in.action_done()
        backorder = self.move_product_in2.picking_id
        self.assertNotEqual(picking, backorder)
        self.assertEqual(self.shipment_advice_in.state, "done")
        self.assertEqual(self.move_product_in1.state, "done")
        self.assertEqual(picking.state, "done")
        self.assertEqual(backorder.state, "assigned")

    def test_shipment_advice_done_full(self):
        """Validating a shipment (whatever the backorder policy is) should
        validate all fully loaded transfers.
        """
        picking = self.move_product_out1.picking_id
        self.progress_shipment_advice(self.shipment_advice_out)
        self.load_records_in_shipment(self.shipment_advice_out, picking)
        self.shipment_advice_out.action_done()
        self.assertEqual(self.shipment_advice_out.state, "done")
        self.assertTrue(
            all(
                move.state == "done"
                for move in self.shipment_advice_out.loaded_move_line_ids
            )
        )
        self.assertEqual(picking.state, "done")

    def test_shipment_advice_done_backorder_policy_disabled(self):
        """Validating a shipment with no backorder policy should let partial
        transfers open.
        """
        # Disable the backorder policy
        company = self.shipment_advice_out.company_id
        company.shipment_advice_outgoing_backorder_policy = "leave_open"
        # Load a transfer partially (here a package)
        package_level = self.move_product_out2.move_line_ids.package_level_id
        self.progress_shipment_advice(self.shipment_advice_out)
        self.load_records_in_shipment(self.shipment_advice_out, package_level)
        # Validate the shipment => the transfer is still open
        self.shipment_advice_out.action_done()
        picking = package_level.picking_id
        self.assertEqual(self.shipment_advice_out.state, "error")
        # Check the transfer
        self.assertTrue(
            all(
                move_line.state == "assigned"
                for move_line in package_level.move_line_ids
            )
        )
        self.assertEqual(picking.state, "assigned")

    def test_shipment_advice_done_backorder_policy_enabled(self):
        """Validating a shipment with the backorder policy enabled should
        validate partial transfers and create a backorder.
        """
        # Enable the backorder policy
        company = self.shipment_advice_out.company_id
        company.shipment_advice_outgoing_backorder_policy = "create_backorder"
        # Load a transfer partially (here a package)
        package_level = self.move_product_out2.move_line_ids.package_level_id
        self.progress_shipment_advice(self.shipment_advice_out)
        self.load_records_in_shipment(self.shipment_advice_out, package_level)
        self.assertEqual(package_level.picking_id, self.move_product_out1.picking_id)
        # Validate the shipment => the transfer is validated, creating a backorder
        self.shipment_advice_out.action_done()
        self.assertEqual(self.shipment_advice_out.state, "done")
        # Check the transfer validated
        picking = package_level.picking_id
        self.assertTrue(
            all(move_line.state == "done" for move_line in package_level.move_line_ids)
        )
        self.assertEqual(picking.state, "done")
        # Check the backorder
        picking2 = self.move_product_out1.picking_id
        self.assertNotEqual(picking, picking2)
        self.assertTrue(
            all(move_line.state == "assigned" for move_line in picking2.move_line_ids)
        )
        self.assertEqual(picking2.state, "assigned")

    def test_shipment_advice_cancel(self):
        self.progress_shipment_advice(self.shipment_advice_out)
        self.shipment_advice_out.action_cancel()
        self.assertEqual(self.shipment_advice_out.state, "cancel")

    def test_shipment_advice_cancel_error(self):
        # Test error case for action_cancel
        with self.assertRaises(UserError):
            self.shipment_advice_out.action_cancel()

    def test_shipment_advice_draft(self):
        with self.assertRaises(UserError):
            self.shipment_advice_out.action_draft()
        self.cancel_shipment_advice(self.shipment_advice_out)
        self.shipment_advice_out.action_draft()
        self.assertEqual(self.shipment_advice_out.state, "draft")

    def test_shipment_name(self):
        self.assertTrue("OUT" in self.shipment_advice_out.name)
        self.assertTrue("IN" in self.shipment_advice_in.name)
