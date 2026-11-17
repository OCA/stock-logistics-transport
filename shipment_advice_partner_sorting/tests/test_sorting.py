# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
from odoo.tests import Form

from odoo.addons.shipment_advice.tests.common import Common


class TestPartnerSorting(Common):
    def test_enable_disable_and_reenable(self):
        shipment = self.shipment_advice_out
        picking = self.move_product_out1.picking_id
        self.assertFalse(shipment.partner_sorting_enabled)
        self.plan_records_in_shipment(shipment, picking)
        self.assertFalse(shipment.planned_partner_order_ids)

        shipment.partner_sorting_enabled = True
        order = shipment.planned_partner_order_ids
        self.assertEqual(order.stock_picking_ids, picking)
        order.sequence = 12

        picking2 = self._create_distinct_picking(
            self.picking_type_out, self.product_out2, 5
        )
        self.plan_records_in_shipment(shipment, picking2)
        self.assertEqual(order.sequence, 12)

        shipment.partner_sorting_enabled = False
        self.assertFalse(shipment.planned_partner_order_ids)
        self.assertFalse(order.exists())
        self.assertEqual(shipment.planned_picking_ids, picking | picking2)

        shipment.partner_sorting_enabled = True
        self.assertEqual(len(shipment.planned_partner_order_ids), 2)
        self.assertNotIn(12, shipment.planned_partner_order_ids.mapped("sequence"))

    def test_onchange_does_not_remove_saved_orders(self):
        shipment = self.shipment_advice_out
        shipment.partner_sorting_enabled = True
        self.plan_records_in_shipment(shipment, self.move_product_out1.picking_id)
        order = shipment.planned_partner_order_ids
        form = Form(shipment)
        form.partner_sorting_enabled = False
        self.assertTrue(order.exists())
        self.assertTrue(shipment.partner_sorting_enabled)

    def test_unplanning_one_of_multiple_partner_pickings_preserves_sequence(self):
        shipment = self.shipment_advice_out
        shipment.partner_sorting_enabled = True
        picking = self.move_product_out1.picking_id
        picking2 = self._create_distinct_picking(
            self.picking_type_out, self.product_out2, 5
        )
        partner = self.env["res.partner"].create({"name": "Shared address"})
        (picking | picking2).partner_id = partner
        self.plan_records_in_shipment(shipment, picking | picking2)
        order = shipment.planned_partner_order_ids
        order.sequence = 17

        self.unplan_records_from_shipment(picking2)

        self.assertEqual(shipment.planned_partner_order_ids, order)
        self.assertEqual(order.sequence, 17)
        self.assertEqual(order.stock_picking_ids, picking)
