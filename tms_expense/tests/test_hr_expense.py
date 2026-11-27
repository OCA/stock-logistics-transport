# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestHrExpenseTrip(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.origin = cls.env["res.partner"].create(
            {"name": "Expense Origin", "tms_location": True}
        )
        cls.destination = cls.env["res.partner"].create(
            {"name": "Expense Destination", "tms_location": True}
        )
        cls.driver = cls.env["tms.driver"].create(
            {"name": "Expense Driver", "phone": "5550001", "is_external": True}
        )
        cls.order = cls.env["tms.order"].create(
            {
                "name": "Expense Trip",
                "company_id": cls.env.company.id,
                "origin_id": cls.origin.id,
                "destination_id": cls.destination.id,
                "driver_id": cls.driver.id,
            }
        )
        cls.employee = cls.env["hr.employee"].create({"name": "Expense Employee"})
        cls.product = cls.env.ref("tms_expense.expense_trip_fuel")
        cls.expense = cls.env["hr.expense"].create(
            {
                "name": "Fuel expense",
                "employee_id": cls.employee.id,
                "product_id": cls.product.id,
                "total_amount": 50.0,
                "trip_id": cls.order.id,
            }
        )

    def test_action_view_order(self):
        action = self.expense.action_view_order()
        self.assertEqual(action["res_model"], "tms.order")
        self.assertEqual(action["res_id"], self.order.id)
        self.assertEqual(action["view_mode"], "form")
        self.assertIn(self.order.name, action["name"])
