# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestTmsExpenseOrder(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.origin = cls.env["res.partner"].create(
            {"name": "Order Origin", "tms_location": True}
        )
        cls.destination = cls.env["res.partner"].create(
            {"name": "Order Destination", "tms_location": True}
        )
        cls.driver = cls.env["tms.driver"].create(
            {"name": "Order Driver", "phone": "5550005", "is_external": False}
        )
        cls.employee = cls.env["hr.employee"].search(
            [("work_contact_id", "=", cls.driver.partner_id.id)], limit=1
        )
        cls.product = cls.env.ref("tms_expense.expense_trip_toll")
        cls.completed_stage = cls.env.ref("tms.tms_stage_order_completed")
        cls.draft_stage = cls.env.ref("tms.tms_stage_order_draft")

    def _create_order(self, **kwargs):
        values = {
            "name": "Order Trip",
            "company_id": self.env.company.id,
            "origin_id": self.origin.id,
            "destination_id": self.destination.id,
            "driver_id": self.driver.id,
        }
        values.update(kwargs)
        return self.env["tms.order"].create(values)

    def _create_expense(self, order):
        return self.env["hr.expense"].create(
            {
                "name": "Toll expense",
                "employee_id": self.employee.id,
                "product_id": self.product.id,
                "total_amount": 25.0,
                "trip_id": order.id,
            }
        )

    def test_compute_driver_employee_id(self):
        order = self._create_order()
        self.assertEqual(order.employee_id, self.employee)

    def test_compute_expense_count(self):
        order = self._create_order()
        self.assertEqual(order.expense_count, 0)
        self._create_expense(order)
        order.invalidate_recordset(["expense_count"])
        self.assertEqual(order.expense_count, 1)

    def test_action_view_expenses(self):
        order = self._create_order()
        self._create_expense(order)
        action = order.action_view_expenses()
        self.assertEqual(action["res_model"], "hr.expense")
        self.assertEqual(action["view_mode"], "list,form")
        self.assertEqual(action["domain"], [("trip_id", "=", order.id)])
        self.assertEqual(action["context"]["default_trip_id"], order.id)
        self.assertIn(order.name, action["name"])

    def test_submit_expenses_on_completed_stage(self):
        order = self._create_order(stage_id=self.draft_stage.id)
        expense = self._create_expense(order)
        self.assertEqual(expense.state, "draft")
        order.write({"stage_id": self.completed_stage.id})
        self.assertNotEqual(expense.state, "draft")

    def test_skip_submit_for_non_draft_expenses(self):
        order = self._create_order(stage_id=self.draft_stage.id)
        expense = self._create_expense(order)
        expense.action_submit()
        state_before = expense.state
        order.write({"stage_id": self.draft_stage.id})
        order.write({"stage_id": self.completed_stage.id})
        self.assertEqual(expense.state, state_before)

    def test_write_without_stage_change(self):
        order = self._create_order(stage_id=self.draft_stage.id)
        expense = self._create_expense(order)
        order.write({"description": "Updated trip"})
        self.assertEqual(expense.state, "draft")

    def test_write_non_completed_stage_does_not_submit(self):
        confirmed_stage = self.env.ref("tms.tms_stage_order_confirmed")
        order = self._create_order(stage_id=self.draft_stage.id)
        expense = self._create_expense(order)
        order.write({"stage_id": confirmed_stage.id})
        self.assertEqual(expense.state, "draft")
