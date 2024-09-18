from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestTMSStage(TransactionCase):
    @classmethod
    def setUpClass(self):
        super().setUpClass()

        # Create a test team
        self.team = self.env["tms.team"].create(
            {
                "name": "Test Team",
            }
        )

        # Create a test company
        self.company = self.env["res.company"].create(
            {
                "name": "Test Company",
            }
        )

    def test_stage_creation(self):
        stage = self.env["tms.stage"].create(
            {
                "name": "Test Stage",
                "stage_type": "order",
                "sequence": 1,
                "company_id": self.company.id,
            }
        )

        self.assertTrue(stage, "Stage wasn't created successfully")
        self.assertEqual(stage.name, "Test Stage", "Stage name should be 'Test Stage'")
        self.assertEqual(stage.stage_type, "order", "Stage type should be 'order'")
        self.assertEqual(stage.sequence, 1, "Stage sequence should be 1")
        self.assertEqual(
            stage.company_id, self.company, "Stage company should be correctly assigned"
        )

    def test_stage_default_team(self):
        stage = self.env["tms.stage"].create(
            {
                "name": "Default Team Stage",
                "stage_type": "order",
                "sequence": 4,
                "tms_team_ids": [(6, 0, [self.team.id])],
            }
        )

        self.assertIn(
            self.team,
            stage.tms_team_ids,
            "Stage should be associated with the test team",
        )

    def test_stage_deletion(self):
        stage = self.env["tms.stage"].create(
            {
                "name": "Deletable Stage",
                "stage_type": "order",
                "sequence": 5,
            }
        )

        self.assertTrue(stage, "Stage wasn't created successfully")
        stage.unlink()

        with self.assertRaises(UserError, msg="You cannot delete default stages."):
            self.env["tms.stage"].create(
                {
                    "name": "Default Stage",
                    "stage_type": "order",
                    "sequence": 6,
                    "is_default": True,
                }
            ).unlink()
