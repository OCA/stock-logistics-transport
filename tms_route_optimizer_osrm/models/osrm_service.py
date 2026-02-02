# Copyright (C) 2025 KMEE (https://kmee.com.br)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

import requests

_logger = logging.getLogger(__name__)


class OSRMService:
    """
    OSRM (Open Source Routing Machine) API client.

    Provides methods for:
    - Getting distance/duration matrices between multiple locations
    - Getting route geometry for visualization (polylines)
    - Route optimization (trip API)

    Default server: https://router.project-osrm.org (public demo server)
    For production, consider self-hosting OSRM.
    """

    DEFAULT_URL = "https://router.project-osrm.org"
    TIMEOUT = 60

    def __init__(self, base_url=None):
        """
        Initialize OSRM service.

        Args:
            base_url: OSRM server URL (default: public server)
        """
        self.base_url = base_url or self.DEFAULT_URL

    def get_distance_matrix(self, locations, profile="driving"):
        """
        Get distance and duration matrix between locations using OSRM Table API.

        Args:
            locations: List of (latitude, longitude) tuples
            profile: Routing profile (driving, walking, cycling)

        Returns:
            dict with:
                - distances: 2D list of distances in meters
                - durations: 2D list of durations in seconds
                - distances_km: 2D list of distances in kilometers (for VRP)
            None if request fails
        """
        if len(locations) < 2:
            return None

        # OSRM expects longitude,latitude order
        coords = ";".join([f"{lon},{lat}" for lat, lon in locations])
        url = f"{self.base_url}/table/v1/{profile}/{coords}"

        params = {
            "annotations": "distance,duration",
        }

        try:
            response = requests.get(url, params=params, timeout=self.TIMEOUT)
            response.raise_for_status()
            data = response.json()

            if data.get("code") != "Ok":
                _logger.warning("OSRM table failed: %s", data.get("message"))
                return None

            # Convert distances from meters to kilometers
            distances = data.get("distances", [])
            distances_km = [
                [d / 1000 if d is not None else None for d in row] for row in distances
            ]

            return {
                "distances": distances,
                "durations": data.get("durations", []),
                "distances_km": distances_km,
            }

        except requests.RequestException as e:
            _logger.warning("OSRM table request failed: %s", e)
            return None

    def get_route(self, waypoints, profile="driving"):
        """
        Get route between waypoints including geometry for polylines.

        Args:
            waypoints: List of (latitude, longitude) tuples
            profile: Routing profile (driving, walking, cycling)

        Returns:
            dict with:
                - geometry: List of [lat, lng] for polyline
                - distance: Total distance in meters
                - duration: Total duration in seconds
                - legs: Route segments
            None if request fails
        """
        if len(waypoints) < 2:
            return None

        # OSRM expects longitude,latitude order
        coords = ";".join([f"{lon},{lat}" for lat, lon in waypoints])
        url = f"{self.base_url}/route/v1/{profile}/{coords}"

        params = {
            "overview": "full",
            "geometries": "geojson",
            "steps": "true",
        }

        try:
            response = requests.get(url, params=params, timeout=self.TIMEOUT)
            response.raise_for_status()
            data = response.json()

            if data.get("code") != "Ok":
                _logger.warning("OSRM route failed: %s", data.get("message"))
                return None

            route = data["routes"][0]

            # Convert GeoJSON coordinates from [lng, lat] to [lat, lng]
            geometry = [
                [coord[1], coord[0]] for coord in route["geometry"]["coordinates"]
            ]

            return {
                "geometry": geometry,
                "distance": route["distance"],
                "duration": route["duration"],
                "legs": [
                    {
                        "distance": leg["distance"],
                        "duration": leg["duration"],
                        "summary": leg.get("summary", ""),
                    }
                    for leg in route["legs"]
                ],
            }

        except requests.RequestException as e:
            _logger.warning("OSRM route request failed: %s", e)
            return None

    def get_optimized_route(self, waypoints, profile="driving", roundtrip=False):
        """
        Get TSP-optimized route visiting all waypoints using OSRM Trip API.

        Args:
            waypoints: List of (latitude, longitude) tuples
            profile: Routing profile
            roundtrip: Whether to return to starting point

        Returns:
            dict with:
                - geometry: List of [lat, lng] for polyline
                - distance: Total distance in meters
                - duration: Total duration in seconds
                - waypoint_order: Optimized order of waypoints
            None if request fails
        """
        if len(waypoints) < 2:
            return None

        # OSRM expects longitude,latitude order
        coords = ";".join([f"{lon},{lat}" for lat, lon in waypoints])
        url = f"{self.base_url}/trip/v1/{profile}/{coords}"

        params = {
            "overview": "full",
            "geometries": "geojson",
            "steps": "true",
            "roundtrip": "true" if roundtrip else "false",
            "source": "first",
            "destination": "last",
        }

        try:
            response = requests.get(url, params=params, timeout=self.TIMEOUT)
            response.raise_for_status()
            data = response.json()

            if data.get("code") != "Ok":
                _logger.warning("OSRM trip failed: %s", data.get("message"))
                return None

            trip = data["trips"][0]

            # Get waypoint ordering
            waypoint_order = [wp["waypoint_index"] for wp in data["waypoints"]]

            # Convert GeoJSON coordinates from [lng, lat] to [lat, lng]
            geometry = [
                [coord[1], coord[0]] for coord in trip["geometry"]["coordinates"]
            ]

            return {
                "geometry": geometry,
                "distance": trip["distance"],
                "duration": trip["duration"],
                "waypoint_order": waypoint_order,
            }

        except requests.RequestException as e:
            _logger.warning("OSRM trip request failed: %s", e)
            return None

    def is_available(self):
        """
        Check if OSRM server is available.

        Returns:
            bool: True if server responds, False otherwise
        """
        try:
            # Simple health check - get route between two close points
            test_coords = "-43.1729,-22.9068;-43.1739,-22.9078"  # Rio de Janeiro
            url = f"{self.base_url}/route/v1/driving/{test_coords}"
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False
