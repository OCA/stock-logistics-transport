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
        self.driver._default_stage_id()

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

    def test_read_group_stage_ids(self):
        stages = self.env["tms.driver"]._read_group_stage_ids(
            self.env["tms.stage"], [], "sequence"
        )
        self.assertIn(self.stage, stages)
        self.assertTrue(all(stage.stage_type == "driver" for stage in stages))

    def test_web_read_group_expands_driver_stages(self):
        result = (
            self.env["tms.driver"]
            .with_context(read_group_expand=True)
            .web_read_group(
                domain=[("is_company", "=", False)],
                groupby=["stage_id"],
                auto_unfold=True,
                opening_info=[],
                unfold_read_specification={"display_name": {}, "is_active": {}},
            )
        )
        self.assertGreater(result["length"], 0)
        self.assertTrue(result["groups"])

    def test_schedule_meeting(self):
        if not hasattr(type(self.driver.partner_id), "schedule_meeting"):
            self.skipTest("calendar module is not installed")
        action = self.driver.schedule_meeting()
        self.assertEqual(action.get("res_model"), "calendar.event")

    def test_create_company_delegates_to_partner(self):
        self.driver.create_company()

    def test_open_commercial_entity_delegates_to_partner(self):
        action = self.driver.open_commercial_entity()
        self.assertEqual(action.get("res_model"), "res.partner")

    def test_geo_localize_delegates_to_partner(self):
        self.driver.geo_localize()

    def test_creation_message(self):
        self.assertEqual(self.driver._creation_message(), "Driver created")

    def test_track_subtype_on_stage_change(self):
        subtype = self.env.ref("tms.mt_driver_stage")
        self.assertEqual(
            self.driver._track_subtype({"stage_id": self.stage.id}),
            subtype,
        )

    def test_track_subtype_returns_false_for_other_fields(self):
        self.assertFalse(self.driver._track_subtype({"driver_type": "terrestrial"}))

    def test_driver_creation_logs_message_in_chatter(self):
        self.env.cr.precommit.run()
        new_driver = self.env["tms.driver"].create({"name": "Chatter Driver"})
        self.env.cr.precommit.run()
        messages = new_driver.message_ids
        self.assertTrue(messages)
        self.assertIn("Driver created", messages[0].body)

    def test_stage_change_logs_subtype(self):
        new_stage = self.env["tms.stage"].create(
            {
                "name": "New Stage",
                "stage_type": "driver",
                "sequence": 2,
            }
        )
        self.env.cr.precommit.run()
        self.driver.write({"stage_id": new_stage.id})
        self.env.cr.precommit.run()
        subtype_messages = self.driver.message_ids.filtered(
            lambda m: m.subtype_id == self.env.ref("tms.mt_driver_stage")
        )
        self.assertTrue(subtype_messages)

    def test_tracked_field_change_logs_message(self):
        self.env.cr.precommit.run()
        before = self.driver.message_ids
        self.driver.write({"is_external": False})
        self.env.cr.precommit.run()
        new_messages = self.driver.message_ids - before
        self.assertTrue(new_messages)
        tracked_fields = {
            field_name
            for message in new_messages
            for field_name in message.tracking_value_ids.field_id.mapped("name")
        }
        self.assertIn("is_external", tracked_fields)
