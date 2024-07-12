# Copyright 2024 Michael Tietz (MT Software) <mtietz@mt-software.de>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from .common import Common


class TestShipmentAdviceAutoClose(Common):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.shipment_advice_in.company_id.shipment_advice_auto_close_incoming = True
        cls.picking1 = cls.move_product_in1.picking_id
        group = cls.env["procurement.group"].create({})
        cls.move_product_in21 = cls._create_move(
            cls.picking_type_in, cls.product_in, 5, group
        )
        cls.picking2 = cls.move_product_in21.picking_id
        cls.pickings = cls.picking1 | cls.picking2
        cls.plan_records_in_shipment(cls.shipment_advice_in, cls.pickings)
        cls.progress_shipment_advice(cls.shipment_advice_in)

    def test_auto_close_incoming_on_done(self):
        self.validate_picking(self.picking1)
        self.assertEqual(self.shipment_advice_in.state, "in_progress")
        self.validate_picking(self.picking2)
        self.assertEqual(self.shipment_advice_in.state, "done")

    def test_auto_close_incoming_on_cancel(self):
        self.validate_picking(self.picking1)
        self.assertEqual(self.shipment_advice_in.state, "in_progress")
        self.picking2.action_cancel()
        self.assertEqual(self.shipment_advice_in.state, "done")

    def test_no_auto_close_on_outgoing(self):
        picking = self.move_product_out1.picking_id
        self.plan_records_in_shipment(self.shipment_advice_out, picking)
        self.progress_shipment_advice(self.shipment_advice_out)
        self.validate_picking(picking)
        self.assertEqual(picking.state, "done")
        self.assertEqual(self.shipment_advice_out.state, "in_progress")

    def test_no_auto_close_context(self):
        pickings = self.pickings.with_context(shipment_advice_ignore_auto_close=True)
        for picking in pickings:
            self.validate_picking(picking)
        self.assertEqual(self.shipment_advice_in.state, "in_progress")
