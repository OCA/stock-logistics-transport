# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import ValidationError

from .common import TestShipmentAdvicePlannerCommon


class TestShipmentAdvicePlanner(TestShipmentAdvicePlannerCommon):
    def test_plan_delivery_and_receipt_together(self):
        delivery = self.pickings.filtered(
            lambda p: (
                p.picking_type_code == "outgoing"
                and p.state == "assigned"
                and p.picking_type_id.warehouse_id == self.warehouse
            )
        )[:1]
        self.assertTrue(delivery)
        partner = delivery.partner_id
        picking_type = self.warehouse.in_type_id
        pickup = self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "location_id": self.env.ref("stock.stock_location_customers").id,
                "location_dest_id": picking_type.default_location_dest_id.id,
                "partner_id": partner.id,
            }
        )
        product = delivery.move_ids[0].product_id
        self.env["stock.move"].create(
            {
                "name": product.name,
                "product_id": product.id,
                "product_uom": product.uom_id.id,
                "product_uom_qty": 1,
                "picking_id": pickup.id,
                "location_id": pickup.location_id.id,
                "location_dest_id": pickup.location_dest_id.id,
            }
        )
        pickup.action_confirm()
        pickup.action_assign()
        self.assertEqual(pickup.state, "assigned")
        self.assertTrue(pickup.can_be_planned_in_shipment_advice)
        self.assertEqual(
            self.env["stock.picking"].search(
                [
                    ("id", "=", pickup.id),
                    ("can_be_planned_in_shipment_advice", "=", True),
                ]
            ),
            pickup,
        )
        self.assertFalse(
            self.env["stock.picking"].search(
                [
                    ("id", "=", pickup.id),
                    ("can_be_planned_in_shipment_advice", "=", False),
                ]
            )
        )
        pickings = delivery | pickup
        wizard = (
            self.env["shipment.advice.planner"]
            .with_context(active_model="stock.picking", active_ids=pickings.ids)
            .create({"warehouse_id": self.warehouse.id})
        )
        self.assertEqual(wizard.picking_to_plan_ids, pickings)
        action = wizard.button_plan_shipments()
        shipment = self.env[action["res_model"]].search(action["domain"])
        self.assertEqual(len(shipment), 1)
        self.assertEqual(shipment.shipment_type, "outgoing")
        self.assertEqual(shipment.planned_picking_ids, pickings)
        self.assertEqual(
            set(shipment.planned_partner_order_ids.mapped("operation_type")),
            {"delivery", "pickup"},
        )
        self.assertFalse(pickup.can_be_planned_in_shipment_advice)
        self.assertEqual(
            self.env["stock.picking"].search(
                [
                    ("id", "=", pickup.id),
                    ("can_be_planned_in_shipment_advice", "=", False),
                ]
            ),
            pickup,
        )
        self.assertFalse(
            self.env["stock.picking"].search(
                [
                    ("id", "=", pickup.id),
                    ("can_be_planned_in_shipment_advice", "=", True),
                ]
            )
        )

    def test_shipment_advice_planner_multi_warehouse(self):
        wizard = self.wizard_form.save()
        action = wizard.button_plan_shipments()
        shipments = self.env[action.get("res_model")].search(action.get("domain"))
        self.assertEqual(len(shipments), 2)
        self.assertEqual(len(shipments.mapped("warehouse_id")), 2)
        self.assertEqual(
            shipments.warehouse_id, self.pickings.picking_type_id.warehouse_id
        )

    def test_shipment_advice_planner_one_warehouse(self):
        self.wizard_form.warehouse_id = self.warehouse
        expected_pickings = self.pickings.filtered(
            lambda picking: (
                picking.can_be_planned_in_shipment_advice
                and picking.picking_type_id.warehouse_id == self.warehouse
            )
        )
        wizard = self.wizard_form.save()
        self.assertEqual(wizard.picking_to_plan_ids, expected_pickings)
        action = wizard.button_plan_shipments()
        self.assertEqual(
            wizard.picking_to_plan_ids.picking_type_id.warehouse_id, self.warehouse
        )
        shipment = self.env[action.get("res_model")].search(action.get("domain"))
        self.assertEqual(len(shipment), 1)
        self.assertEqual(shipment.warehouse_id, self.warehouse)

    def test_shipment_advice_planner_dock(self):
        with self.assertRaises(
            AssertionError, msg="dock is invisible if warehouse is unset"
        ):
            self.wizard_form.dock_id = self.dock
        self.wizard_form.warehouse_id = self.warehouse
        self.wizard_form.dock_id = self.dock
        wizard = self.wizard_form.save()
        action = wizard.button_plan_shipments()
        self.assertEqual(
            wizard.picking_to_plan_ids.picking_type_id.warehouse_id, self.warehouse
        )
        shipment = self.env[action.get("res_model")].search(action.get("domain"))
        self.assertEqual(shipment.dock_id, self.dock)

    def test_check_warehouse(self):
        self.wizard_form.warehouse_id = self.warehouse
        with self.assertRaises(
            ValidationError, msg="transfers must belong to the selected warehouse"
        ):
            self.wizard_form.picking_to_plan_ids.add(
                self.pickings.filtered(
                    lambda p, w=self.warehouse2: p.picking_type_id.warehouse_id == w
                )[0]
            )
        self.wizard_form.warehouse_id = self.warehouse2
        with self.assertRaises(
            ValidationError, msg="dock must belong to the selected warehouse"
        ):
            self.wizard_form.dock_id = self.dock

    def test_check_picking_to_plan(self):
        with self.assertRaises(
            ValidationError,
            msg="The transfers selected must be ready and of the delivery type",
        ):
            self.wizard_form.picking_to_plan_ids.add(
                self.pickings.filtered(
                    lambda p: not p.can_be_planned_in_shipment_advice
                )[0]
            )
