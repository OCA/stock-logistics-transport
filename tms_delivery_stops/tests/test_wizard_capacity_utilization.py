# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestWizardCapacityUtilization(TransactionCase):
    """Test cases for Create Order wizard capacity utilization."""

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
        cls.vehicle = cls.env["fleet.vehicle"].create(
            {
                "name": "Test Vehicle",
                "model_id": cls.env.ref("fleet.model_astra").id,
                "weight_capacity": 1000.0,
                "volume_capacity": 10.0,
            }
        )
        # Create unallocated stops
        cls.stop1 = cls.env["tms.order.stop"].create(
            {
                "partner_id": cls.partner.id,
                "weight": 300.0,
                "volume": 3.0,
            }
        )
        cls.stop2 = cls.env["tms.order.stop"].create(
            {
                "partner_id": cls.partner.id,
                "weight": 200.0,
                "volume": 2.0,
            }
        )

    def test_wizard_totals_computed(self):
        """Test wizard computes totals from selected stops."""
        wizard = self.env["tms.order.from.stops"].create(
            {
                "tms_team_id": self.tms_team.id,
                "stop_ids": [(6, 0, [self.stop1.id, self.stop2.id])],
            }
        )
        self.assertEqual(wizard.total_weight, 500.0)
        self.assertEqual(wizard.total_volume, 5.0)

    def test_wizard_utilization_with_vehicle(self):
        """Test wizard shows utilization when vehicle selected."""
        wizard = self.env["tms.order.from.stops"].create(
            {
                "tms_team_id": self.tms_team.id,
                "vehicle_id": self.vehicle.id,
                "stop_ids": [(6, 0, [self.stop1.id, self.stop2.id])],
            }
        )
        self.assertEqual(wizard.weight_utilization, 50.0)
        self.assertEqual(wizard.volume_utilization, 50.0)

    def test_wizard_utilization_without_vehicle(self):
        """Test wizard shows 0% when no vehicle selected."""
        wizard = self.env["tms.order.from.stops"].create(
            {
                "tms_team_id": self.tms_team.id,
                "stop_ids": [(6, 0, [self.stop1.id, self.stop2.id])],
            }
        )
        self.assertEqual(wizard.weight_utilization, 0.0)
        self.assertEqual(wizard.volume_utilization, 0.0)

    def test_wizard_capacity_from_vehicle(self):
        """Test wizard shows capacity from selected vehicle."""
        wizard = self.env["tms.order.from.stops"].create(
            {
                "tms_team_id": self.tms_team.id,
                "vehicle_id": self.vehicle.id,
                "stop_ids": [(6, 0, [self.stop1.id, self.stop2.id])],
            }
        )
        self.assertEqual(wizard.weight_capacity, 1000.0)
        self.assertEqual(wizard.volume_capacity, 10.0)
