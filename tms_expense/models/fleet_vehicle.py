# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle"

    def _reallocate_fuel_expenses(self, extra=None):
        if self.env.context.get("tms_reallocating_fuel"):
            return
        expenses = self.env["hr.expense"]
        if self:
            expenses = self.env["hr.expense"].search(
                [
                    ("vehicle_id", "in", self.ids),
                    ("product_id.tms_spread_by_distance", "=", True),
                ]
            )
        if extra:
            expenses |= extra
        if expenses:
            reallocating = expenses.with_context(tms_reallocating_fuel=True)
            reallocating._rebuild_fuel_allocations()
