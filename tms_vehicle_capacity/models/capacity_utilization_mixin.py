# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class CapacityUtilizationMixin(models.AbstractModel):
    """Mixin for calculating vehicle capacity utilization."""

    _name = "capacity.utilization.mixin"
    _description = "Capacity Utilization Mixin"

    weight_capacity = fields.Float(
        string="Weight Capacity (kg)",
        compute="_compute_capacity_from_vehicle",
    )
    volume_capacity = fields.Float(
        string="Volume Capacity (m³)",
        compute="_compute_capacity_from_vehicle",
    )
    weight_utilization = fields.Float(
        string="Weight Utilization (%)",
        compute="_compute_utilization",
    )
    volume_utilization = fields.Float(
        string="Volume Utilization (%)",
        compute="_compute_utilization",
    )

    def _get_vehicle_for_capacity(self):
        """Hook: return the vehicle for capacity calculation. Override if needed."""
        return getattr(self, "vehicle_id", False)

    def _get_total_weight(self):
        """Hook: return total weight. Override if needed."""
        return getattr(self, "total_weight", 0.0)

    def _get_total_volume(self):
        """Hook: return total volume. Override if needed."""
        return getattr(self, "total_volume", 0.0)

    @api.depends("vehicle_id")
    def _compute_capacity_from_vehicle(self):
        for record in self:
            vehicle = record._get_vehicle_for_capacity()
            record.weight_capacity = vehicle.weight_capacity if vehicle else 0.0
            record.volume_capacity = vehicle.volume_capacity if vehicle else 0.0

    @api.depends("vehicle_id")
    def _compute_utilization(self):
        for record in self:
            record.weight_utilization = self._calculate_utilization_percentage(
                record._get_total_weight(), record.weight_capacity
            )
            record.volume_utilization = self._calculate_utilization_percentage(
                record._get_total_volume(), record.volume_capacity
            )

    @staticmethod
    def _calculate_utilization_percentage(actual, capacity):
        """Calculate utilization percentage. Returns 0 if no capacity."""
        if not capacity:
            return 0.0
        return (actual / capacity) * 100
