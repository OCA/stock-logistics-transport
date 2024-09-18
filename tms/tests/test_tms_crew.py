from odoo.tests.common import TransactionCase


class TestTMSCrew(TransactionCase):
    @classmethod
    def setUpClass(self):
        super().setUpClass()

        self.company = self.env["res.company"].create(
            {
                "name": "Test Company",
            }
        )

        self.driver1 = self.env["tms.driver"].create(
            {
                "name": "Driver 1",
                "company_id": self.company.id,
            }
        )
        self.driver2 = self.env["tms.driver"].create(
            {
                "name": "Driver 2",
                "company_id": self.company.id,
            }
        )

        self.personnel1 = self.env["res.partner"].create(
            {
                "name": "Personnel 1",
                "company_id": self.company.id,
            }
        )
        self.personnel2 = self.env["res.partner"].create(
            {
                "name": "Personnel 2",
                "company_id": self.company.id,
            }
        )

        self.vehicle = self.env["fleet.vehicle"].create(
            {
                "name": "Test Vehicle",
                "company_id": self.company.id,
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

        self.team = self.env["tms.team"].create(
            {
                "name": "Test Team",
                "company_id": self.company.id,
            }
        )
        self.crew = self.env["tms.crew"].create(
            {
                "name": "Test Crew",
                "driver_ids": [(6, 0, [self.driver1.id, self.driver2.id])],
                "personnel_ids": [(6, 0, [self.personnel1.id, self.personnel2.id])],
                "default_vehicle_id": self.vehicle.id,
                "company_id": self.company.id,
                "tms_team_id": self.team.id,
            }
        )

    def test_crew_creation(self):
        self.assertTrue(self.crew, "Crew wasn't created successfully")
        self.assertEqual(self.crew.name, "Test Crew", "Crew name should be 'Test Crew'")
        self.assertIn(
            self.driver1,
            self.crew.driver_ids,
            "Driver 1 should be assigned to the crew",
        )
        self.assertIn(
            self.driver2,
            self.crew.driver_ids,
            "Driver 2 should be assigned to the crew",
        )
        self.assertIn(
            self.personnel1,
            self.crew.personnel_ids,
            "Personnel 1 should be assigned to the crew",
        )
        self.assertIn(
            self.personnel2,
            self.crew.personnel_ids,
            "Personnel 2 should be assigned to the crew",
        )
        self.assertEqual(
            self.crew.default_vehicle_id,
            self.vehicle,
            "Default vehicle should be assigned correctly",
        )
        self.assertEqual(
            self.crew.company_id,
            self.company,
            "Crew should belong to the correct company",
        )
        self.assertEqual(
            self.crew.tms_team_id,
            self.team,
            "Crew should be assigned to the correct team",
        )
