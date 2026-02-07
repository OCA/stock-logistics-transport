# Copyright (C) 2025 KMEE (https://kmee.com.br)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests.common import TransactionCase


class TestDistanceConfigSettings(TransactionCase):
    """Tests for distance provider configuration settings."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

    def test_default_provider_is_haversine(self):
        """Default distance provider should be haversine."""
        provider = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("tms.distance_provider", "haversine")
        )
        self.assertEqual(provider, "haversine")

    def test_settings_save_provider(self):
        """Saving config settings should persist the provider parameter."""
        settings = self.env["res.config.settings"].create(
            {"tms_distance_provider": "osrm"}
        )
        settings.set_values()

        provider = (
            self.env["ir.config_parameter"].sudo().get_param("tms.distance_provider")
        )
        self.assertEqual(provider, "osrm")

    def test_settings_save_osrm_url(self):
        """Saving settings should persist OSRM URL."""
        custom_url = "https://my-osrm.example.com"
        settings = self.env["res.config.settings"].create(
            {"tms_osrm_server_url": custom_url}
        )
        settings.set_values()

        url = self.env["ir.config_parameter"].sudo().get_param("tms.osrm_server_url")
        self.assertEqual(url, custom_url)

    def test_settings_load_values(self):
        """Loading settings should read from config parameters."""
        self.env["ir.config_parameter"].sudo().set_param(
            "tms.distance_provider", "osrm"
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "tms.osrm_server_url", "https://custom-osrm.test"
        )

        settings = self.env["res.config.settings"].create({})
        settings.get_values()

        self.assertEqual(settings.tms_distance_provider, "osrm")
        self.assertEqual(settings.tms_osrm_server_url, "https://custom-osrm.test")

    def test_config_sync_use_osrm_on_distance_matrix(self):
        """Distance config should sync use_osrm flag when computing matrix."""
        self.env["ir.config_parameter"].sudo().set_param(
            "tms.distance_provider", "osrm"
        )

        optimizer = self.env["tms.route.optimizer"].new({})

        # If use_osrm field exists (OSRM module installed)
        if hasattr(optimizer, "use_osrm"):
            optimizer.use_osrm = False
            # Computing distance matrix should sync the flag
            locations = [(-23.55, -46.63), (-22.90, -43.17)]
            optimizer._compute_distance_matrix(locations)
            self.assertTrue(optimizer.use_osrm)
