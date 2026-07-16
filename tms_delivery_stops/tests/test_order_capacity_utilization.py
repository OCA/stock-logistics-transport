# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestTMSOrderCapacityUtilization(TransactionCase):
    """Test cases for TMS Order capacity utilization."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Test Partner",
                "city": "Test City",
            }
        )
        cls.tms_team = cls.env["tms.team"].create(
            {
                "name": "Test Team",
            }
        )
        # Create vehicle with capacity
        cls.vehicle = cls.env["fleet.vehicle"].create(
            {
                "name": "Test Vehicle",
                "model_id": cls.env.ref("fleet.model_astra").id,
                "weight_capacity": 1000.0,  # 1000 kg
                "volume_capacity": 10.0,  # 10 m3
            }
        )

    def test_order_utilization_with_vehicle(self):
        """Test order utilization when vehicle is assigned."""
        order = self.env["tms.order"].create(
            {
                "tms_team_id": self.tms_team.id,
                "vehicle_id": self.vehicle.id,
            }
        )
        # Create stops
        self.env["tms.order.stop"].create(
            {
                "order_id": order.id,
                "partner_id": self.partner.id,
                "weight": 300.0,
                "volume": 3.0,
            }
        )
        self.env["tms.order.stop"].create(
            {
                "order_id": order.id,
                "partner_id": self.partner.id,
                "weight": 200.0,
                "volume": 2.0,
            }
        )
        # Force recompute
        order.invalidate_recordset()
        # Check totals
        self.assertEqual(order.total_weight, 500.0)
        self.assertEqual(order.total_volume, 5.0)
        # Check utilization (500/1000 = 50%, 5/10 = 50%)
        self.assertEqual(order.weight_utilization, 50.0)
        self.assertEqual(order.volume_utilization, 50.0)

    def test_order_utilization_without_vehicle(self):
        """Test order utilization when no vehicle is assigned."""
        order = self.env["tms.order"].create(
            {
                "tms_team_id": self.tms_team.id,
            }
        )
        self.env["tms.order.stop"].create(
            {
                "order_id": order.id,
                "partner_id": self.partner.id,
                "weight": 500.0,
                "volume": 5.0,
            }
        )
        order.invalidate_recordset()
        # Without vehicle, utilization should be 0
        self.assertEqual(order.weight_utilization, 0.0)
        self.assertEqual(order.volume_utilization, 0.0)

    def test_order_utilization_vehicle_change(self):
        """Test that utilization recalculates when vehicle changes."""
        order = self.env["tms.order"].create(
            {
                "tms_team_id": self.tms_team.id,
                "vehicle_id": self.vehicle.id,
            }
        )
        self.env["tms.order.stop"].create(
            {
                "order_id": order.id,
                "partner_id": self.partner.id,
                "weight": 500.0,
                "volume": 5.0,
            }
        )
        order.invalidate_recordset()
        self.assertEqual(order.weight_utilization, 50.0)

        # Create larger vehicle
        large_vehicle = self.env["fleet.vehicle"].create(
            {
                "name": "Large Vehicle",
                "model_id": self.env.ref("fleet.model_astra").id,
                "weight_capacity": 2000.0,
                "volume_capacity": 20.0,
            }
        )
        # Change vehicle
        order.vehicle_id = large_vehicle
        order.invalidate_recordset()
        # Now utilization should be 25%
        self.assertEqual(order.weight_utilization, 25.0)
        self.assertEqual(order.volume_utilization, 25.0)

    def test_order_utilization_over_capacity(self):
        """Test utilization shows over 100% when overloaded."""
        order = self.env["tms.order"].create(
            {
                "tms_team_id": self.tms_team.id,
                "vehicle_id": self.vehicle.id,
            }
        )
        self.env["tms.order.stop"].create(
            {
                "order_id": order.id,
                "partner_id": self.partner.id,
                "weight": 1500.0,  # Over capacity
                "volume": 15.0,  # Over capacity
            }
        )
        order.invalidate_recordset()
        self.assertEqual(order.weight_utilization, 150.0)
        self.assertEqual(order.volume_utilization, 150.0)
