# Copyright (C) 2025 KMEE (https://kmee.com.br)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import json
import logging

from odoo import api, fields, models

# Import parent's helper class
from odoo.addons.tms_route_optimizer.models.tms_route_optimizer_ortools import (
    RouteOptimizerHelper,
)

# Import shared OSRM service from web_leaflet_lib
from odoo.addons.web_leaflet_lib.models.osrm_service import OSRMService

_logger = logging.getLogger(__name__)


class TMSRouteOptimizer(models.TransientModel):
    """
    Extend TMS Route Optimizer to use OSRM for real road distances.

    When this module is installed, the optimizer will automatically use OSRM
    to calculate distances instead of Haversine (straight-line) distances.

    If OSRM is unavailable, it falls back to Haversine.
    """

    _inherit = "tms.route.optimizer"

    use_osrm = fields.Boolean(
        string="Use OSRM (Road Distances)",
        default=True,
        help="Use OSRM for real road distances instead of straight-line distances. "
        "Provides more accurate results but requires OSRM server availability.",
    )

    route_geometries = fields.Text(
        string="Route Geometries (JSON)",
        readonly=True,
        help="GeoJSON geometries for route visualization.",
    )

    @api.model
    def _get_osrm_url(self):
        """
        Get OSRM server URL from configuration.

        Priority:
            1. tms.osrm_server_url (TMS-specific config)
            2. leaflet.osrm_url (shared Leaflet config)
            3. OSRMService.DEFAULT_URL (public server)
        """
        config = self.env["ir.config_parameter"].sudo()
        return (
            config.get_param("tms.osrm_server_url")
            or config.get_param("leaflet.osrm_url")
            or OSRMService.DEFAULT_URL
        )

    @api.model
    def _get_osrm_service(self):
        """Get configured OSRM service instance."""
        url = self._get_osrm_url()
        return OSRMService(base_url=url)

    def _compute_distance_matrix(self, locations):
        """
        Calculate distance matrix using OSRM if available, otherwise Haversine.

        Override of parent method to use OSRM road distances.

        Args:
            locations: List of (latitude, longitude) tuples

        Returns:
            2D list of distances in kilometers
        """
        if not self.use_osrm:
            return super()._compute_distance_matrix(locations)

        osrm = self._get_osrm_service()

        # Try OSRM first
        result = osrm.get_distance_matrix(locations)

        if result and result.get("distances_km"):
            _logger.info(
                "Using OSRM distances for %d locations",
                len(locations),
            )

            # Handle potential None values in OSRM response
            distances_km = result["distances_km"]
            for i, row in enumerate(distances_km):
                for j, dist in enumerate(row):
                    if dist is None:
                        # Fall back to Haversine for this pair
                        lat1, lon1 = locations[i]
                        lat2, lon2 = locations[j]
                        distances_km[i][j] = RouteOptimizerHelper.haversine_distance(
                            lat1, lon1, lat2, lon2
                        )

            return distances_km

        # Fallback to Haversine
        _logger.warning(
            "OSRM unavailable, falling back to Haversine distances for %d locations",
            len(locations),
        )
        return super()._compute_distance_matrix(locations)

    def _get_route_geometry(self, coordinates):
        """
        Get route geometry from OSRM for visualization.

        Args:
            coordinates: List of (latitude, longitude) tuples representing route

        Returns:
            List of [lat, lng] points for polyline, or None if unavailable
        """
        if not self.use_osrm or len(coordinates) < 2:
            return None

        osrm = self._get_osrm_service()
        result = osrm.get_route(coordinates)

        if result and result.get("geometry"):
            return result["geometry"]

        return None

    def _get_route_info(self, coordinates):
        """
        Get detailed route information from OSRM.

        Args:
            coordinates: List of (latitude, longitude) tuples

        Returns:
            dict with distance (meters), duration (seconds), geometry
        """
        if not self.use_osrm or len(coordinates) < 2:
            # Fallback: calculate Haversine distance
            total_distance = 0
            for i in range(len(coordinates) - 1):
                lat1, lon1 = coordinates[i]
                lat2, lon2 = coordinates[i + 1]
                total_distance += RouteOptimizerHelper.haversine_distance(
                    lat1, lon1, lat2, lon2
                )
            return {
                "distance": total_distance * 1000,  # Convert to meters
                "duration": total_distance * 60,  # Estimate: 60 sec/km
                "geometry": None,
            }

        osrm = self._get_osrm_service()
        result = osrm.get_route(coordinates)

        if result:
            return result

        # Fallback if OSRM fails
        total_distance = 0
        for i in range(len(coordinates) - 1):
            lat1, lon1 = coordinates[i]
            lat2, lon2 = coordinates[i + 1]
            total_distance += RouteOptimizerHelper.haversine_distance(
                lat1, lon1, lat2, lon2
            )
        return {
            "distance": total_distance * 1000,
            "duration": total_distance * 60,
            "geometry": None,
        }

    def _create_result_records(self, solution, vehicles, locations, stop_ids):
        """
        Override to also store route geometries for visualization after creating
        result records.
        """
        result = super()._create_result_records(solution, vehicles, locations, stop_ids)
        self._store_route_geometries(locations, stop_ids, solution)
        return result

    def _store_route_geometries(self, locations, stop_ids, solution):
        """
        Fetch and store OSRM route geometries for each route in the solution.
        """
        if not self.use_osrm:
            return

        geometries = {}
        results = self.env["tms.route.optimizer.result"].search(
            [("optimizer_id", "=", self.id)]
        )

        for idx, record in enumerate(results):
            if idx >= len(solution.get("routes", [])):
                break

            route = solution["routes"][idx]
            route_coords = [locations[node] for node in route["route"]]

            geometry = self._get_route_geometry(route_coords)
            if geometry:
                geometries[record.id] = geometry

        if geometries:
            self.route_geometries = json.dumps(geometries)
