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
            self.assertEqual(settings[f"module_{name}"], module.state in installed)
        arch = self.env.ref("tms.res_config_settings_view_form").arch
        self.assertIn("module_tms_telematics", arch)
        self.assertIn("module_tms_telematics_geotab", arch)
        self.assertIn('invisible="not module_tms_telematics"', arch)

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
        self.assertIn('invisible="not module_tms_telematics"', arch)

    def test_portal_module_is_offered(self):
        settings = self.env["res.config.settings"].create({})
        self.assertIn("module_tms_portal", settings._fields)
        module = self.env["ir.module.module"].search([("name", "=", "tms_portal")])
        installed = ("installed", "to install", "to upgrade")
        self.assertEqual(settings.module_tms_portal, module.state in installed)
        arch = self.env.ref("tms.res_config_settings_view_form").arch
        self.assertIn("module_tms_portal", arch)

    def test_routing_modules_are_offered(self):
        settings = self.env["res.config.settings"].create({})
        self.assertIn("module_tms_routing", settings._fields)
        self.assertIn("module_tms_routing_ors", settings._fields)
        installed = ("installed", "to install", "to upgrade")
        for name in ("tms_routing", "tms_routing_ors"):
            module = self.env["ir.module.module"].search([("name", "=", name)])
            self.assertEqual(settings[f"module_{name}"], module.state in installed)
        arch = self.env.ref("tms.res_config_settings_view_form").arch
        self.assertIn("module_tms_routing", arch)
        self.assertIn("module_tms_routing_ors", arch)
        self.assertIn('invisible="not module_tms_routing"', arch)
