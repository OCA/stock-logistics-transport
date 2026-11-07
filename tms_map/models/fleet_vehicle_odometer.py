# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class FleetVehicleOdometer(models.Model):
    _inherit = "fleet.vehicle.odometer"

    def _invalidate_vehicle_position(self, vehicles):
        vehicles.invalidate_recordset(
            ["tms_last_latitude", "tms_last_longitude", "tms_motion"]
        )

    @api.model_create_multi
    def create(self, vals_list):
        logs = super().create(vals_list)
        self._invalidate_vehicle_position(logs.vehicle_id)
        return logs

    def write(self, vals):
        vehicles = self.vehicle_id
        result = super().write(vals)
        self._invalidate_vehicle_position(vehicles | self.vehicle_id)
        return result

    def unlink(self):
        vehicles = self.vehicle_id
        result = super().unlink()
        self._invalidate_vehicle_position(vehicles)
        return result
