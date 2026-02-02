# Copyright (C) 2025 KMEE (https://kmee.com.br)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from unittest.mock import MagicMock, patch

from odoo.tests.common import TransactionCase

from ..models.osrm_service import OSRMService


class TestOSRMService(TransactionCase):
    """Tests for the OSRM Service."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.osrm = OSRMService()

    def test_osrm_service_init_default(self):
        """Test OSRM service initializes with default URL."""
        osrm = OSRMService()
        self.assertEqual(osrm.base_url, "https://router.project-osrm.org")

    def test_osrm_service_init_custom_url(self):
        """Test OSRM service with custom URL."""
        custom_url = "https://my-osrm-server.com"
        osrm = OSRMService(base_url=custom_url)
        self.assertEqual(osrm.base_url, custom_url)

    def test_distance_matrix_insufficient_locations(self):
        """Test distance matrix with less than 2 locations."""
        result = self.osrm.get_distance_matrix([(0, 0)])
        self.assertIsNone(result)

    @patch("odoo.addons.tms_route_optimizer_osrm.models.osrm_service.requests.get")
    def test_distance_matrix_success(self, mock_get):
        """Test successful distance matrix calculation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": "Ok",
            "distances": [
                [0, 10000, 20000],
                [10000, 0, 15000],
                [20000, 15000, 0],
            ],
            "durations": [
                [0, 600, 1200],
                [600, 0, 900],
                [1200, 900, 0],
            ],
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        locations = [
            (-22.9068, -43.1729),  # Rio de Janeiro
            (-23.5505, -46.6333),  # Sao Paulo
            (-19.9167, -43.9345),  # Belo Horizonte
        ]

        result = self.osrm.get_distance_matrix(locations)

        self.assertIsNotNone(result)
        self.assertIn("distances", result)
        self.assertIn("durations", result)
        self.assertIn("distances_km", result)

        # Check conversion to km
        self.assertEqual(result["distances_km"][0][1], 10.0)  # 10000m = 10km

    @patch("odoo.addons.tms_route_optimizer_osrm.models.osrm_service.requests.get")
    def test_get_route_success(self, mock_get):
        """Test successful route calculation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": "Ok",
            "routes": [
                {
                    "geometry": {
                        "coordinates": [
                            [-43.1729, -22.9068],
                            [-43.5, -23.0],
                            [-46.6333, -23.5505],
                        ]
                    },
                    "distance": 430000,
                    "duration": 18000,
                    "legs": [
                        {
                            "distance": 430000,
                            "duration": 18000,
                            "summary": "BR-116",
                        }
                    ],
                }
            ],
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        waypoints = [
            (-22.9068, -43.1729),  # Rio de Janeiro
            (-23.5505, -46.6333),  # Sao Paulo
        ]

        result = self.osrm.get_route(waypoints)

        self.assertIsNotNone(result)
        self.assertIn("geometry", result)
        self.assertIn("distance", result)
        self.assertIn("duration", result)

        # Check geometry is in [lat, lng] format
        self.assertEqual(result["geometry"][0], [-22.9068, -43.1729])

    @patch("odoo.addons.tms_route_optimizer_osrm.models.osrm_service.requests.get")
    def test_get_route_insufficient_waypoints(self, mock_get):
        """Test route calculation with insufficient waypoints."""
        result = self.osrm.get_route([(-22.9068, -43.1729)])
        self.assertIsNone(result)
        mock_get.assert_not_called()

    @patch("odoo.addons.tms_route_optimizer_osrm.models.osrm_service.requests.get")
    def test_get_optimized_route_success(self, mock_get):
        """Test successful TSP route optimization."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": "Ok",
            "trips": [
                {
                    "geometry": {
                        "coordinates": [
                            [-43.1729, -22.9068],
                            [-43.9345, -19.9167],
                            [-46.6333, -23.5505],
                        ]
                    },
                    "distance": 600000,
                    "duration": 25000,
                }
            ],
            "waypoints": [
                {"waypoint_index": 0},
                {"waypoint_index": 2},
                {"waypoint_index": 1},
            ],
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        waypoints = [
            (-22.9068, -43.1729),  # Rio de Janeiro
            (-23.5505, -46.6333),  # Sao Paulo
            (-19.9167, -43.9345),  # Belo Horizonte
        ]

        result = self.osrm.get_optimized_route(waypoints)

        self.assertIsNotNone(result)
        self.assertIn("geometry", result)
        self.assertIn("waypoint_order", result)
        self.assertEqual(result["waypoint_order"], [0, 2, 1])

    @patch("odoo.addons.tms_route_optimizer_osrm.models.osrm_service.requests.get")
    def test_is_available_success(self, mock_get):
        """Test OSRM server availability check."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        self.assertTrue(self.osrm.is_available())

    @patch("odoo.addons.tms_route_optimizer_osrm.models.osrm_service.requests.get")
    def test_is_available_failure(self, mock_get):
        """Test OSRM server unavailability."""
        import requests

        mock_get.side_effect = requests.RequestException("Connection error")

        self.assertFalse(self.osrm.is_available())
