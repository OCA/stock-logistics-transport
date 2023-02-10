# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import Form, TransactionCase


class TestShipmentAdvicePlannerCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.pickings = cls.env["stock.picking"].search([])
        cls.context = {
            "active_ids": cls.pickings.ids,
            "active_model": "stock.picking",
        }
        cls.warehouse = cls.env.ref("stock.warehouse0")
        cls.warehouse2 = cls.env.ref("stock.stock_warehouse_shop0")
        cls.dock = cls.env.ref("shipment_advice.stock_dock_demo")

    def setUp(self):
        super().setUp()
        self.wizard_form = Form(
            self.env["shipment.advice.planner"].with_context(**self.context)
        )
