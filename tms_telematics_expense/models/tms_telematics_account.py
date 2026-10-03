# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.tools.float_utils import float_compare


class TmsTelematicsAccount(models.Model):
    _inherit = "tms.telematics.account"

    def _create_reading(self, device, payload):
        reading = super()._create_reading(device, payload)
        cost = payload.get("fuel_cost")
        if cost:
            reading.fuel_cost = cost
        return reading

    def _apply_fill(self, reading):
        reading.ensure_one()
        if reading.expense_id:
            return True
        expense = self._create_fill_expense(reading)
        if expense:
            reading.sudo().expense_id = expense
        return True

    def _create_fill_expense(self, reading):
        """Turn one fill into the fuel expense that distance allocation splits."""
        self.ensure_one()
        vehicle = reading.device_id.vehicle_id
        product = self.env.ref(
            "tms_expense.expense_trip_fuel", raise_if_not_found=False
        )
        if not vehicle or not product:
            return self.env["hr.expense"]
        if (
            float_compare(reading.fuel_liters, 0, precision_digits=2) <= 0
            and float_compare(reading.fuel_cost, 0, precision_digits=2) <= 0
        ):
            return self.env["hr.expense"]
        trip = self._fill_trip(vehicle, reading)
        driver = trip.driver_id or vehicle.tms_driver_id
        employee = self._employee_for_driver(driver)
        if not employee:
            return self.env["hr.expense"]
        quantity = reading.fuel_liters or 1.0
        amount = self._fill_amount(reading, product)
        vals = {
            "name": self._fill_expense_name(reading),
            "employee_id": employee.id,
            "product_id": product.id,
            "quantity": quantity,
            "total_amount_currency": amount,
            "vehicle_id": vehicle.id,
            "company_id": reading.company_id.id,
            "date": self._fill_date(reading),
        }
        if trip:
            vals["trip_id"] = trip.id
        odometer = self._fill_odometer(vehicle, reading)
        if odometer:
            vals["odometer_id"] = odometer.id
        return self.env["hr.expense"].sudo().create(vals)

    def _fill_expense_name(self, reading):
        if reading.fuel_liters:
            return self.env._("Fuel %(liters)s L", liters=reading.fuel_liters)
        return self.env._("Fuel")

    def _fill_date(self, reading):
        if reading.timestamp:
            return fields.Date.to_date(reading.timestamp)
        return fields.Date.context_today(self)

    def _fill_amount(self, reading, product):
        if float_compare(reading.fuel_cost, 0, precision_digits=2) > 0:
            return reading.fuel_cost
        if reading.fuel_liters and product.standard_price:
            return reading.fuel_liters * product.standard_price
        return 0.0

    def _fill_trip(self, vehicle, reading):
        trips = self.env["tms.order"]
        if reading.odometer_km:
            value = self._to_vehicle_unit(vehicle, reading.odometer_km)
            candidates = trips.search(
                [
                    ("vehicle_id", "=", vehicle.id),
                    ("odometer_start_id", "!=", False),
                ]
            )
            covering = candidates.filtered(
                lambda trip: trip.odometer_start <= value
                and (not trip.odometer_end_id or trip.odometer_end >= value)
            )
            if covering:
                return covering.sorted(key=lambda trip: (trip.odometer_start, trip.id))[
                    :1
                ]
        return trips.search(self._open_trip_domain(vehicle), order="id", limit=1)

    def _fill_odometer(self, vehicle, reading):
        logs = self.env["fleet.vehicle.odometer"]
        if not reading.odometer_km:
            return logs
        value = self._to_vehicle_unit(vehicle, reading.odometer_km)
        for log in logs.search(
            [("vehicle_id", "=", vehicle.id)],
            order="date desc, id desc",
        ):
            if float_compare(log.value, value, precision_digits=1) == 0:
                return log
        return logs

    def _employee_for_driver(self, driver):
        employees = self.env["hr.employee"]
        if not driver:
            return employees
        employee = employees.search(
            [("work_contact_id", "=", driver.partner_id.id)],
            limit=1,
        )
        if employee:
            return employee
        driver.create_driver_employee(driver)
        return employees.search(
            [("work_contact_id", "=", driver.partner_id.id)],
            limit=1,
        )

    @api.model
    def _demo_import_fills(self):
        account = self.env.ref(
            "tms_telematics.demo_telematics_account", raise_if_not_found=False
        )
        device = self.env.ref(
            "tms_telematics.demo_telematics_device", raise_if_not_found=False
        )
        if not account or not device or not device.vehicle_id:
            return self.env["tms.telematics.reading"]
        return account.apply_readings(
            [
                {
                    "external_id": "demo-fill-open",
                    "device_external_id": device.external_id,
                    "event": "fill",
                    "timestamp": "2026-09-01T08:00:00Z",
                    "odometer_km": 100000,
                    "fuel_liters": 100,
                    "fuel_cost": 2000,
                },
                {
                    "external_id": "demo-fill-close",
                    "device_external_id": device.external_id,
                    "event": "fill",
                    "timestamp": "2026-09-10T18:30:00Z",
                    "odometer_km": 100400,
                    "fuel_liters": 180,
                    "fuel_cost": 4500,
                },
            ]
        )
