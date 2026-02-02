# Copyright (C) 2025 KMEE (https://kmee.com.br)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import api, fields, models

# Import parent's helper class
from odoo.addons.tms_route_optimizer.models.tms_route_optimizer_ortools import (
    RouteOptimizerHelper,
)

from .osrm_service import OSRMService

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
        """Get OSRM server URL from configuration."""
        config = self.env["ir.config_parameter"].sudo()
        return config.get_param(
            "tms.osrm_server_url", "https://router.project-osrm.org"
        )

    @api.model
    def _get_osrm_service(self):
        """Get configured OSRM service instance."""
        url = self._get_osrm_url()
        return OSRMService(base_url=url)

    def _calculate_distance_matrix(self, locations):
        """
        Calculate distance matrix using OSRM if available, otherwise Haversine.

        Override of parent method to use OSRM road distances.

        Args:
            locations: List of (latitude, longitude) tuples

        Returns:
            2D list of distances in kilometers
        """
        if not self.use_osrm:
            return RouteOptimizerHelper.calculate_distance_matrix(locations)

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
        return RouteOptimizerHelper.calculate_distance_matrix(locations)

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

    def _store_optimization_results(self, result, vehicles, stop_ids, locations):
        """
        Override to also store route geometries for visualization.
        """
        # Call parent method first
        records = super()._store_optimization_results(
            result, vehicles, stop_ids, locations
        )

        # If OSRM is enabled, fetch and store route geometries
        if self.use_osrm and records:
            import json

            geometries = {}

            for record in records:
                # Get coordinates for this route's stops
                route_coords = []

                # Start from depot
                start_location = self.start_location_id
                if start_location:
                    route_coords.append(
                        (
                            start_location.partner_latitude,
                            start_location.partner_longitude,
                        )
                    )

                # Add stops in order
                for stop in record.stop_ids:
                    if stop.partner_id:
                        route_coords.append(
                            (
                                stop.partner_id.partner_latitude,
                                stop.partner_id.partner_longitude,
                            )
                        )

                # End location
                end_location = self.end_location_id or start_location
                if end_location:
                    route_coords.append(
                        (
                            end_location.partner_latitude,
                            end_location.partner_longitude,
                        )
                    )

                # Get geometry from OSRM
                geometry = self._get_route_geometry(route_coords)
                if geometry:
                    geometries[record.id] = geometry

            if geometries:
                self.route_geometries = json.dumps(geometries)

        return records
