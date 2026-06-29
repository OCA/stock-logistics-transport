# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestTmsExpenseDriver(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

    def test_create_internal_driver_creates_employee(self):
        driver = self.env["tms.driver"].create(
            {"name": "Internal Driver", "phone": "5550002", "is_external": False}
        )
        employee = self.env["hr.employee"].search(
            [("work_contact_id", "=", driver.partner_id.id)], limit=1
        )
        self.assertTrue(employee)
        self.assertEqual(employee.name, "Internal Driver")
        self.assertIn(employee, driver.partner_id.employee_ids)

    def test_create_driver_employee_skips_existing(self):
        driver = self.env["tms.driver"].create(
            {
                "name": "Existing Employee Driver",
                "phone": "5550003",
                "is_external": True,
            }
        )
        existing = self.env["hr.employee"].create({"name": "Existing Employee Driver"})
        driver.create_driver_employee(driver)
        employees = self.env["hr.employee"].search([("name", "=", driver.name)])
        self.assertEqual(len(employees), 1)
        self.assertEqual(employees, existing)

    def test_update_existing_drivers_as_employees(self):
        driver = self.env["tms.driver"].create(
            {"name": "Legacy Driver", "phone": "5550004", "is_external": True}
        )
        self.assertFalse(
            self.env["hr.employee"].search([("name", "=", driver.name)], limit=1)
        )
        self.env["tms.driver"].update_existing_drivers_as_employees()
        employee = self.env["hr.employee"].search([("name", "=", driver.name)], limit=1)
        self.assertTrue(employee)
        self.assertEqual(employee.work_contact_id, driver.partner_id)
