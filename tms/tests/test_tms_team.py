from odoo.tests.common import TransactionCase


class TestTMSTeam(TransactionCase):
    @classmethod
    def setUpClass(self):
        super().setUpClass()

        self.stage1 = self.env["tms.stage"].create(
            {
                "name": "Stage 1",
                "stage_type": "driver",
                "sequence": 1,
                "is_default": True,
            }
        )
        self.stage2 = self.env["tms.stage"].create(
            {
                "name": "Stage 2",
                "stage_type": "driver",
                "sequence": 2,
            }
        )

        self.crew = self.env["tms.crew"].create(
            {
                "name": "Test Crew",
            }
        )

        self.vehicle = self.env["fleet.vehicle"].create(
            {
                "model_id": self.env["fleet.vehicle.model"]
                .create(
                    {
                        "name": "Test Model",
                        "brand_id": self.env["fleet.vehicle.model.brand"]
                        .create({"name": "Test Brand"})
                        .id,
                    }
                )
                .id,
            }
        )

        self.driver = self.env["tms.driver"].create(
            {"name": "Test Driver", "tms_team_id": False}
        )

        self.order = self.env["tms.order"].create(
            {
                "name": "Test Order",
                "tms_team_id": False,
                "stage_id": self.stage1.id,
            }
        )

        self.team = self.env["tms.team"].create(
            {
                "name": "Test Team",
                "description": "A team for testing purposes",
                "stage_ids": [(6, 0, [self.stage1.id, self.stage2.id])],
                "vehicle_ids": [(6, 0, [self.vehicle.id])],
                "driver_ids": [(6, 0, [self.driver.id])],
                "order_ids": [(6, 0, [self.order.id])],
                "crew_ids": [(6, 0, [self.crew.id])],
            }
        )

    def test_team_creation(self):
        self.assertTrue(self.team, "Team wasn't created successfully")
        self.assertEqual(self.team.name, "Test Team", "Team name should be 'Test Team'")
        self.assertEqual(
            self.team.description,
            "A team for testing purposes",
            "Team description should be 'A team for testing purposes'",
        )
        self.assertIn(self.stage1, self.team.stage_ids, "Team should have stage1")
        self.assertIn(self.stage2, self.team.stage_ids, "Team should have stage2")
        self.assertIn(
            self.vehicle, self.team.vehicle_ids, "Team should have the test vehicle"
        )
        self.assertIn(
            self.driver, self.team.driver_ids, "Team should have the test driver"
        )
        self.assertIn(
            self.order, self.team.order_ids, "Team should have the test order"
        )
        self.assertIn(self.crew, self.team.crew_ids, "Team should have the test crew")

    def test_order_count(self):
        self.team.write({"order_ids": [(6, 0, [self.order.id])]})
        self.assertEqual(self.team.order_count, 1, "Order count should be 1")

    def test_driver_count(self):
        self.team.write({"driver_ids": [(6, 0, [self.driver.id])]})
        self.assertEqual(self.team.driver_count, 1, "Driver count should be 1")

    def test_vehicle_count(self):
        self.team.write({"vehicle_ids": [(6, 0, [self.vehicle.id])]})
        self.assertEqual(self.team.vehicle_count, 1, "Vehicle count should be 1")

    def test_default_stages(self):
        self.assertIn(
            self.stage1, self.team.stage_ids, "Default stage1 should be in team stages"
        )
        self.assertIn(
            self.stage2, self.team.stage_ids, "Default stage2 should be in team stages"
        )
