# Copyright (C) 2018 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def create(self, vals):
        driver = super().create(vals)
        if driver.tms_type == "driver":
            self.create_driver_employee(driver)
        return driver

    @api.model
    def update_existing_drivers_as_employees(self):
        drivers = self.search([("tms_type", "=", "driver")])
        for driver in drivers:
            self.create_driver_employee(driver)

    def create_driver_employee(self, partner):
        employee = self.env["hr.employee"].search(
            [("name", "=", partner.name)], limit=1
        )

        if not employee:
            employee_id = self.env["hr.employee"].create(
                {
                    "name": partner.name,
                    "work_email": partner.email,
                    "work_phone": partner.phone,
                    "work_contact_id": partner.id,
                }
            )
            partner.employee_ids = [(4, employee_id.id)]
