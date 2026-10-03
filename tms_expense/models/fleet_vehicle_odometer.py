# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class FleetVehicleOdometer(models.Model):
    _inherit = "fleet.vehicle.odometer"

    def write(self, vals):
        result = super().write(vals)
        if {"value", "vehicle_id"} & set(vals):
            self.mapped("vehicle_id")._reallocate_fuel_expenses()
        return result
