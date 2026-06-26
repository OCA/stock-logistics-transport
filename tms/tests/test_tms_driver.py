from unittest.mock import patch

from odoo.tests.common import TransactionCase


class TestTmsDriver(TransactionCase):
    @classmethod
    def setUpClass(self):
        super().setUpClass()

        self.stage = self.env["tms.stage"].create(
            {
                "name": "Test Stage",
                "stage_type": "driver",
                "sequence": 1,
            }
        )

        self.driver = self.env["tms.driver"].create(
            {
                "name": "Test Driver",
                "is_external": True,
                "driver_type": "terrestrial",
                "driver_license_number": "ABC123456",
                "driver_license_type": "B",
                "distance_traveled": 1000,
                "distance_traveled_uom": "km",
                "driving_experience_years": 5,
            }
        )

    def test_driver_creation(self):
        self.assertTrue(self.driver, "Driver wasn't created successfully")
        self.assertEqual(
            self.driver.name, "Test Driver", "Driver name should be 'Test Driver'"
        )
        self.assertTrue(self.driver.is_external, "Driver should be marked as external")
        self.assertEqual(
            self.driver.driver_type,
            "terrestrial",
            "Driver type should be 'terrestrial'",
        )
        self.assertEqual(
            self.driver.driver_license_number,
            "ABC123456",
            "Driver license number should be 'ABC123456'",
        )
        self.assertEqual(
            self.driver.driver_license_type, "B", "Driver license type should be 'B'"
        )
        self.assertEqual(
            self.driver.distance_traveled, 1000, "Distance traveled should be 1000"
        )
        self.assertEqual(
            self.driver.driving_experience_years,
            5,
            "Driving experience years should be 5",
        )
        self.assertTrue(
            self.driver.stage_id, "Driver stage should be correctly assigned"
        )

    def test_driver_default_is_active(self):
        driver = self.env["tms.driver"].create({"name": "Active Driver"})
        self.assertTrue(driver.is_active)
        self.assertFalse(driver.is_training)

    def test_default_stage_id(self):
        stage_id = self.env["tms.driver"]._default_stage_id()
        self.assertEqual(stage_id, self.stage.id)

    def test_read_group_stage_ids(self):
        stages = self.env["tms.driver"]._read_group_stage_ids(
            self.env["tms.stage"], [], "sequence"
        )
        self.assertIn(self.stage, stages)
        self.assertTrue(all(stage.stage_type == "driver" for stage in stages))

    def test_schedule_meeting_delegates_to_partner(self):
        expected_action = {
            "type": "ir.actions.act_window",
            "res_model": "calendar.event",
        }
        partner_model = type(self.env["res.partner"])
        with patch.object(
            partner_model,
            "schedule_meeting",
            lambda self: expected_action,
            create=True,
        ):
            action = self.driver.schedule_meeting()
        self.assertEqual(action, expected_action)

    def test_schedule_meeting_with_calendar(self):
        if not hasattr(type(self.driver.partner_id), "schedule_meeting"):
            self.skipTest("calendar module is not installed")
        action = self.driver.schedule_meeting()
        self.assertEqual(action.get("res_model"), "calendar.event")
        partner_ids = action.get("context", {}).get("default_partner_ids", [])
        self.assertIn(self.driver.partner_id.id, partner_ids)
