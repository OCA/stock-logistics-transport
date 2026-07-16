# Copyright (C) 2018 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class TmsDriver(models.Model):
    _inherit = "tms.driver"

    @api.model_create_multi
    def create(self, vals_list):
        drivers = super().create(vals_list)
        for driver, vals in zip(drivers, vals_list, strict=True):
            if not vals.get("is_external"):
                driver.create_driver_employee(driver)
        return drivers

    @api.model
    def update_existing_drivers_as_employees(self):
        drivers = self.env["tms.driver"].search([("id", "!=", False)])
        for driver in drivers:
            driver.create_driver_employee(driver)

    def create_driver_employee(self, driver):
        employee = self.env["hr.employee"].search([("name", "=", driver.name)], limit=1)

        if not employee:
            employee_id = self.env["hr.employee"].create(
                {
                    "name": driver.name,
                    "work_email": driver.email,
                    "work_phone": driver.phone,
                    "work_contact_id": driver.partner_id.id,
                }
            )
            driver.partner_id.employee_ids = [(4, employee_id.id)]
