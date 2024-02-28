# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from odoo.tests.common import Form, TransactionCase


class TestShipmentAdvicePlannerToursolverCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.pickings = cls.env["stock.picking"].search([])
        cls.context = {
            "active_ids": cls.pickings.ids,
            "active_model": "stock.picking",
        }
        cls.warehouse = cls.env.ref("stock.warehouse0")
        cls.resource_1 = cls.env.ref(
            "shipment_advice_planner_toursolver.toursolver_resource_r1_demo"
        )
        cls.resource_2 = cls.env.ref(
            "shipment_advice_planner_toursolver.toursolver_resource_r2_demo"
        )

    def setUp(self):
        super().setUp()
        self.wizard_form = Form(
            self.env["shipment.advice.planner"].with_context(**self.context)
        )
        self.wizard_form.warehouse_id = self.warehouse

    def _create_task(self):
        self.wizard_form.shipment_planning_method = "toursolver"
        wizard = self.wizard_form.save()
        wizard.delivery_resource_ids = self.resource_1 | self.resource_2
        wizard.button_plan_shipments()
        return wizard.picking_to_plan_ids.toursolver_task_id
