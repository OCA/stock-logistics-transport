# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestResConfigSettings(TransactionCase):
    def test_telematics_modules_are_offered(self):
        settings = self.env["res.config.settings"].create({})
        self.assertIn("module_tms_telematics", settings._fields)
        self.assertIn("module_tms_telematics_geotab", settings._fields)
        installed = ("installed", "to install", "to upgrade")
        for name in ("tms_telematics", "tms_telematics_geotab"):
            module = self.env["ir.module.module"].search([("name", "=", name)])
            self.assertEqual(
                settings["module_%s" % name], module.state in installed
            )
        arch = self.env.ref("tms.res_config_settings_view_form").arch
        self.assertIn("module_tms_telematics", arch)
        self.assertIn("module_tms_telematics_geotab", arch)
        self.assertIn("invisible=\"not module_tms_telematics\"", arch)

    def test_telematics_expense_module_is_offered(self):
        settings = self.env["res.config.settings"].create({})
        self.assertIn("module_tms_telematics_expense", settings._fields)
        module = self.env["ir.module.module"].search(
            [("name", "=", "tms_telematics_expense")]
        )
        installed = ("installed", "to install", "to upgrade")
        self.assertEqual(
            settings.module_tms_telematics_expense,
            bool(module) and module.state in installed,
        )
        arch = self.env.ref("tms.res_config_settings_view_form").arch
        self.assertIn("module_tms_telematics_expense", arch)
        self.assertIn("invisible=\"not module_tms_telematics\"", arch)

    def test_map_module_is_offered(self):
        settings = self.env["res.config.settings"].create({})
        self.assertIn("module_tms_map", settings._fields)
        module = self.env["ir.module.module"].search([("name", "=", "tms_map")])
        installed = ("installed", "to install", "to upgrade")
        self.assertEqual(
            settings.module_tms_map,
            bool(module) and module.state in installed,
        )
        arch = self.env.ref("tms.res_config_settings_view_form").arch
        self.assertIn("module_tms_map", arch)

    def test_mode_settings_grant_groups_to_internal_users(self):
        names = (
            "group_tms_road_user",
            "group_tms_air_user",
            "group_tms_water_user",
            "group_tms_rail_user",
        )
        settings = self.env["res.config.settings"].create({})
        for name in names:
            self.assertIn(name, settings._fields)
            self.assertTrue(settings[name])
        arch = self.env.ref("tms.res_config_settings_view_form").arch
        for name in names:
            self.assertIn(name, arch)
        internal = self.env.ref("base.group_user")
        road = self.env.ref("tms.group_tms_road_user")
        self.assertIn(road, internal.all_implied_ids)
        self.env["res.config.settings"].create(
            {"group_tms_road_user": False}
        ).set_values()
        internal.invalidate_recordset()
        self.assertNotIn(road, internal.all_implied_ids)
        user = self.env["res.users"].create(
            {
                "name": "Road Off",
                "login": "road_off_mode",
                "group_ids": [(6, 0, [internal.id])],
            }
        )
        self.assertFalse(user.has_group("tms.group_tms_road_user"))
        self.assertTrue(user.has_group("tms.group_tms_air_user"))
        self.env["res.config.settings"].create(
            {"group_tms_road_user": True}
        ).set_values()
        internal.invalidate_recordset()
        self.assertIn(road, internal.all_implied_ids)
