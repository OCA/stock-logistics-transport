# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import ValidationError

from .common import TestShipmentAdvicePlannerCommon


class TestShipmentAdvicePlanner(TestShipmentAdvicePlannerCommon):
    def test_shipment_advice_planner_multi_warehouse(self):
        wizard = self.wizard_form.save()
        action = wizard.button_plan_shipments()
        shipments = self.env[action.get("res_model")].search(action.get("domain"))
        self.assertEqual(len(shipments), 2)
        self.assertEqual(len(shipments.warehouse_id), 2)
        self.assertEqual(
            shipments.warehouse_id, self.pickings.picking_type_id.warehouse_id
        )

    def test_shipment_advice_planner_one_warehouse(self):
        self.wizard_form.warehouse_id = self.warehouse
        self.assertEqual(len(self.wizard_form.picking_to_plan_ids), 11)
        wizard = self.wizard_form.save()
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
