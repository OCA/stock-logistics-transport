# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase

from ..models.capacity_utilization_mixin import CapacityUtilizationMixin


class TestCapacityUtilizationMixin(TransactionCase):
    """Test cases for capacity utilization mixin."""

    def test_calculate_utilization_percentage_normal(self):
        """Test utilization calculation with valid values."""
        # 50% utilization
        result = CapacityUtilizationMixin._calculate_utilization_percentage(500, 1000)
        self.assertEqual(result, 50.0)

    def test_calculate_utilization_percentage_full(self):
        """Test 100% utilization."""
        result = CapacityUtilizationMixin._calculate_utilization_percentage(1000, 1000)
        self.assertEqual(result, 100.0)

    def test_calculate_utilization_percentage_over_capacity(self):
        """Test over 100% utilization (overloaded)."""
        result = CapacityUtilizationMixin._calculate_utilization_percentage(1500, 1000)
        self.assertEqual(result, 150.0)

    def test_calculate_utilization_percentage_zero_capacity(self):
        """Test with zero capacity returns 0."""
        result = CapacityUtilizationMixin._calculate_utilization_percentage(500, 0)
        self.assertEqual(result, 0.0)

    def test_calculate_utilization_percentage_none_capacity(self):
        """Test with None capacity returns 0."""
        result = CapacityUtilizationMixin._calculate_utilization_percentage(500, None)
        self.assertEqual(result, 0.0)

    def test_calculate_utilization_percentage_zero_actual(self):
        """Test with zero actual value."""
        result = CapacityUtilizationMixin._calculate_utilization_percentage(0, 1000)
        self.assertEqual(result, 0.0)
