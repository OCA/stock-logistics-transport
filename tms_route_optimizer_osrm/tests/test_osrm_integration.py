# Copyright (C) 2025 KMEE (https://kmee.com.br)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from unittest.mock import MagicMock, patch

from odoo.tests.common import TransactionCase


class TestOSRMIntegration(TransactionCase):
    """Tests for OSRM integration with TMS Route Optimizer."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.team = cls.env["tms.team"].create({"name": "OSRM Test Team"})

    def _create_optimizer(self, vals=None):
        defaults = {"team_id": self.team.id}
        if vals:
            defaults.update(vals)
        return self.env["tms.route.optimizer"].create(defaults)

    def test_optimizer_uses_osrm_by_default(self):
        """Test that the optimizer uses OSRM when module is installed."""
        optimizer = self._create_optimizer()
        self.assertTrue(optimizer.use_osrm)

    def test_optimizer_can_disable_osrm(self):
        """Test that OSRM can be disabled in the optimizer."""
        optimizer = self._create_optimizer({"use_osrm": False})
        self.assertFalse(optimizer.use_osrm)

    def test_get_osrm_url_from_config(self):
        """Test OSRM URL is read from config parameters."""
        custom_url = "https://my-osrm-server.example.com"
        self.env["ir.config_parameter"].sudo().set_param(
            "tms.osrm_server_url", custom_url
        )

        optimizer = self._create_optimizer()
        url = optimizer._get_osrm_url()

        self.assertEqual(url, custom_url)

    def test_get_osrm_url_default(self):
        """Test OSRM URL defaults to public server."""
        self.env["ir.config_parameter"].sudo().set_param("tms.osrm_server_url", False)

        optimizer = self._create_optimizer()
        url = optimizer._get_osrm_url()

        self.assertEqual(url, "https://router.project-osrm.org")

    @patch(
        "odoo.addons.tms_route_optimizer_osrm.models.tms_route_optimizer."
        "TMSRouteOptimizer._get_osrm_service"
    )
    def test_compute_distance_matrix_osrm_success(self, mock_get_service):
        """Test distance matrix calculation uses OSRM when available."""
        mock_osrm = MagicMock()
        mock_osrm.get_distance_matrix.return_value = {
            "distances_km": [
                [0, 10, 20],
                [10, 0, 15],
                [20, 15, 0],
            ]
        }
        mock_get_service.return_value = mock_osrm

        optimizer = self._create_optimizer({"use_osrm": True})

        locations = [
            (-22.9068, -43.1729),
            (-23.5505, -46.6333),
            (-19.9167, -43.9345),
        ]

        result = optimizer._compute_distance_matrix(locations)

        self.assertIsNotNone(result)
        self.assertEqual(result[0][1], 10)
        mock_osrm.get_distance_matrix.assert_called_once_with(locations)

    @patch(
        "odoo.addons.tms_route_optimizer_osrm.models.tms_route_optimizer."
        "TMSRouteOptimizer._get_osrm_service"
    )
    def test_compute_distance_matrix_fallback_haversine(self, mock_get_service):
        """Test distance matrix falls back to Haversine if OSRM fails."""
        mock_osrm = MagicMock()
        mock_osrm.get_distance_matrix.return_value = None
        mock_get_service.return_value = mock_osrm

        optimizer = self._create_optimizer({"use_osrm": True})

        locations = [
            (-22.9068, -43.1729),
            (-23.5505, -46.6333),
        ]

        result = optimizer._compute_distance_matrix(locations)

        self.assertIsNotNone(result)
        # Haversine distance between Rio and SP is ~357 km
        self.assertGreater(result[0][1], 300)
        self.assertLess(result[0][1], 400)

    @patch(
        "odoo.addons.tms_route_optimizer_osrm.models.tms_route_optimizer."
        "TMSRouteOptimizer._get_osrm_service"
    )
    def test_compute_distance_matrix_osrm_disabled(self, mock_get_service):
        """Test distance matrix uses Haversine when OSRM is disabled."""
        optimizer = self._create_optimizer({"use_osrm": False})

        locations = [
            (-22.9068, -43.1729),
            (-23.5505, -46.6333),
        ]

        result = optimizer._compute_distance_matrix(locations)

        self.assertIsNotNone(result)
        mock_get_service.assert_not_called()

    @patch(
        "odoo.addons.tms_route_optimizer_osrm.models.tms_route_optimizer."
        "TMSRouteOptimizer._get_osrm_service"
    )
    def test_get_route_geometry_success(self, mock_get_service):
        """Test route geometry retrieval from OSRM."""
        mock_osrm = MagicMock()
        mock_osrm.get_route.return_value = {
            "geometry": [
                [-22.9068, -43.1729],
                [-23.0, -44.0],
                [-23.5505, -46.6333],
            ],
            "distance": 430000,
            "duration": 18000,
        }
        mock_get_service.return_value = mock_osrm

        optimizer = self._create_optimizer({"use_osrm": True})

        coordinates = [
            (-22.9068, -43.1729),
            (-23.5505, -46.6333),
        ]

        result = optimizer._get_route_geometry(coordinates)

        self.assertIsNotNone(result)
        self.assertEqual(len(result), 3)

    @patch(
        "odoo.addons.tms_route_optimizer_osrm.models.tms_route_optimizer."
        "TMSRouteOptimizer._get_osrm_service"
    )
    def test_get_route_geometry_osrm_disabled(self, mock_get_service):
        """Test route geometry returns None when OSRM is disabled."""
        optimizer = self._create_optimizer({"use_osrm": False})

        coordinates = [
            (-22.9068, -43.1729),
            (-23.5505, -46.6333),
        ]

        result = optimizer._get_route_geometry(coordinates)

        self.assertIsNone(result)
        mock_get_service.assert_not_called()

    @patch(
        "odoo.addons.tms_route_optimizer_osrm.models.tms_route_optimizer."
        "TMSRouteOptimizer._get_osrm_service"
    )
    def test_get_route_info_success(self, mock_get_service):
        """Test route info retrieval from OSRM."""
        mock_osrm = MagicMock()
        mock_osrm.get_route.return_value = {
            "geometry": [
                [-22.9068, -43.1729],
                [-23.5505, -46.6333],
            ],
            "distance": 430000,
            "duration": 18000,
        }
        mock_get_service.return_value = mock_osrm

        optimizer = self._create_optimizer({"use_osrm": True})

        coordinates = [
            (-22.9068, -43.1729),
            (-23.5505, -46.6333),
        ]

        result = optimizer._get_route_info(coordinates)

        self.assertIsNotNone(result)
        self.assertEqual(result["distance"], 430000)
        self.assertEqual(result["duration"], 18000)

    @patch(
        "odoo.addons.tms_route_optimizer_osrm.models.tms_route_optimizer."
        "TMSRouteOptimizer._get_osrm_service"
    )
    def test_get_route_info_fallback(self, mock_get_service):
        """Test route info falls back to Haversine estimate if OSRM fails."""
        mock_osrm = MagicMock()
        mock_osrm.get_route.return_value = None
        mock_get_service.return_value = mock_osrm

        optimizer = self._create_optimizer({"use_osrm": True})

        coordinates = [
            (-22.9068, -43.1729),
            (-23.5505, -46.6333),
        ]

        result = optimizer._get_route_info(coordinates)

        self.assertIsNotNone(result)
        # Distance should be Haversine in meters (around 357 km = 357000 m)
        self.assertGreater(result["distance"], 300000)
        self.assertLess(result["distance"], 400000)
        # Geometry should be None in fallback
        self.assertIsNone(result.get("geometry"))

    def test_osrm_handles_null_distances(self):
        """Test optimizer handles null distances from OSRM by falling back."""
        with patch(
            "odoo.addons.tms_route_optimizer_osrm.models.tms_route_optimizer."
            "TMSRouteOptimizer._get_osrm_service"
        ) as mock_get_service:
            mock_osrm = MagicMock()
            mock_osrm.get_distance_matrix.return_value = {
                "distances_km": [
                    [0, None],
                    [None, 0],
                ]
            }
            mock_get_service.return_value = mock_osrm

            optimizer = self._create_optimizer({"use_osrm": True})

            locations = [
                (-22.9068, -43.1729),
                (-23.5505, -46.6333),
            ]

            result = optimizer._compute_distance_matrix(locations)

            self.assertIsNotNone(result)
            # Null values should be replaced with Haversine fallback
            self.assertIsNotNone(result[0][1])
            self.assertGreater(result[0][1], 300)

    @patch(
        "odoo.addons.tms_route_optimizer_osrm.models.tms_route_optimizer."
        "TMSRouteOptimizer._get_osrm_service"
    )
    def test_compute_distance_matrix_delegates_to_super_when_disabled(
        self, mock_get_service
    ):
        """Test that disabling OSRM delegates to super() (Haversine by default)."""
        optimizer = self._create_optimizer({"use_osrm": False})

        locations = [
            (-22.9068, -43.1729),
            (-23.5505, -46.6333),
        ]

        result = optimizer._compute_distance_matrix(locations)

        # Should return valid Haversine distances without calling OSRM
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)
        self.assertEqual(len(result[0]), 2)
        self.assertAlmostEqual(result[0][0], 0.0, places=1)
        self.assertGreater(result[0][1], 0)
        mock_get_service.assert_not_called()
