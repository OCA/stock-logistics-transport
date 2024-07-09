# Copyright 2024 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import fields

from odoo.addons.shipment_advice.tests.common import Common


class TestShipmentAdviceReceptionPlanner(Common):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.shipment = cls.shipment_advice_in
        cls.partner = cls.env.ref("base.res_partner_3")
        cls.product1 = cls.env.ref("product.product_product_25")
        cls.product2 = cls.env.ref("product.product_product_27")
        cls.purchase1 = cls.env["purchase.order"].create(
            {
                "partner_id": cls.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product1.id,
                            "product_uom": cls.product1.uom_id.id,
                            "name": cls.product1.name,
                            "price_unit": cls.product1.standard_price,
                            "product_qty": 42.0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product2.id,
                            "product_uom": cls.product2.uom_id.id,
                            "name": cls.product2.name,
                            "price_unit": cls.product2.standard_price,
                            "product_qty": 12.0,
                        },
                    ),
                ],
            }
        )
        cls.purchase1.button_confirm()
        cls.picking = cls.purchase1.picking_ids
        cls.move_product1 = cls.picking.move_lines.filtered(
            lambda move: move.product_id == cls.product1
        )
        cls.move_product2 = cls.picking.move_lines.filtered(
            lambda move: move.product_id == cls.product2
        )

    def _plan_reception(self, shipment_advice):
        wiz_model = self.env["wizard.plan.reception.shipment"].with_context(
            active_model=shipment_advice._name,
            active_ids=shipment_advice.ids,
        )
        wiz = wiz_model.create({"shipment_advice_id": shipment_advice.id})
        return wiz

    def test_shipment_advice_reception_planner_1(self):
        """Check planning a move for reception."""
        self.arrival_date = fields.Datetime.to_datetime("2038-01-19")
        self.shipment.arrival_date = self.arrival_date
        wizard = self._plan_reception(self.shipment)
        wizard.move_ids = [(4, self.move_product1.id, 0)]
        wizard.action_plan_reception()
        self.assertEqual(self.move_product1.shipment_advice_id, self.shipment)
        # Check the scheduled date on the move has changed
        self.assertEqual(self.move_product1.date, self.shipment.arrival_date)
        # And changing the arrival date on the shipment will change the scheduled date
        self.arrival_date = fields.Datetime.to_datetime("2038-01-20")
        self.shipment.arrival_date = self.arrival_date
        self.assertEqual(self.move_product1.date, self.arrival_date)

    def test_shipment_advice_reception_split_move(self):
        self.arrival_date = fields.Datetime.to_datetime("2038-01-19")
        self.shipment.arrival_date = self.arrival_date
        wizard = self._plan_reception(self.shipment)
        wizard.move_ids = [(4, self.move_product1.id, 0)]
        # Only receive some of the products
        wizard.move_to_split_ids = [
            (0, 0, {"move_id": self.move_product1.id, "quantity_to_split": 20})
        ]
        wizard.action_plan_reception()
        # The original move should not be in the shipment
        self.assertFalse(self.move_product1.shipment_advice_id)
        self.assertEqual(self.move_product1.product_uom_qty, 42 - 20)
        new_split_move = (
            self.purchase1.picking_ids.move_lines
            - self.move_product1
            - self.move_product2
        )
        self.assertEqual(new_split_move.shipment_advice_id, self.shipment)
        self.assertEqual(new_split_move.product_uom_qty, 20)
        self.assertEqual(new_split_move.state, "assigned")

        # Unplanning the previously planned move, should merge them back.
        self.unplan_records_from_shipment(new_split_move)
        move = self.picking.move_lines.filtered(
            lambda move: move.product_id == self.product1
        )
        self.assertTrue(len(move) == 1)
        self.assertEqual(move.product_uom_qty, 42)
