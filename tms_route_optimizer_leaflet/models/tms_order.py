# Copyright (C) 2025 KMEE (https://kmee.com.br)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import json
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class TMSOrder(models.Model):
    """
    Extend TMS Order with Leaflet map visualization support.

    Adds computed fields for map display and route polylines.
    """

    _inherit = "tms.order"

    # Computed fields for leaflet_map view
    map_latitude = fields.Float(
        compute="_compute_map_coordinates",
        store=True,
    )
    map_longitude = fields.Float(
        compute="_compute_map_coordinates",
        store=True,
    )
    map_display_address = fields.Char(
        string="Map Address",
        compute="_compute_map_display",
    )
    route_geometry_json = fields.Text(
        string="Route Geometry",
        compute="_compute_route_geometry",
        help="GeoJSON geometry of the optimized route for map visualization.",
    )
    route_summary = fields.Char(
        compute="_compute_route_summary",
    )

    @api.depends(
        "origin_id", "origin_id.partner_latitude", "origin_id.partner_longitude"
    )
    def _compute_map_coordinates(self):
        """
        Compute map center coordinates from origin location.
        Uses origin as the primary location for the order marker.
        """
        for order in self:
            if order.origin_id:
                order.map_latitude = order.origin_id.partner_latitude or 0.0
                order.map_longitude = order.origin_id.partner_longitude or 0.0
            else:
                order.map_latitude = 0.0
                order.map_longitude = 0.0

    @api.depends("origin_id", "destination_id")
    def _compute_map_display(self):
        """Compute display address for map popup."""
        for order in self:
            parts = []
            if order.origin_id:
                parts.append(f"From: {order.origin_id.display_name}")
            if order.destination_id:
                parts.append(f"To: {order.destination_id.display_name}")
            order.map_display_address = " | ".join(parts) if parts else ""

    @api.depends("stop_ids", "stop_ids.sequence", "origin_id", "destination_id")
    def _compute_route_geometry(self):
        """
        Compute route geometry for polyline visualization.

        Gets route from OSRM if available, otherwise returns straight lines.
        """
        for order in self:
            coordinates = order._get_route_coordinates()

            if len(coordinates) < 2:
                order.route_geometry_json = False
                continue

            # Try to get real route geometry via OSRM
            geometry = order._get_osrm_route_geometry(coordinates)

            if geometry:
                order.route_geometry_json = json.dumps(geometry)
            else:
                # Fallback: straight lines between points
                order.route_geometry_json = json.dumps(coordinates)

    @api.depends("stop_ids")
    def _compute_route_summary(self):
        """Compute summary text for route."""
        for order in self:
            stop_count = len(order.stop_ids or [])

            parts = []
            if stop_count:
                parts.append(f"{stop_count} stops")

            order.route_summary = " • ".join(parts) if parts else ""

    def _get_route_coordinates(self):
        """
        Get ordered list of coordinates for the route.

        Returns:
            List of [lat, lng] pairs
        """
        self.ensure_one()
        coordinates = []

        # Start from origin (both zero means not geocoded)
        if self.origin_id and (
            self.origin_id.partner_latitude or self.origin_id.partner_longitude
        ):
            coordinates.append(
                [self.origin_id.partner_latitude, self.origin_id.partner_longitude]
            )

        # Add stops in sequence order
        for stop in (self.stop_ids or []).sorted("sequence"):
            partner = stop.partner_id
            if partner and (partner.partner_latitude or partner.partner_longitude):
                coordinates.append(
                    [partner.partner_latitude, partner.partner_longitude]
                )

        # End at destination
        if self.destination_id and (
            self.destination_id.partner_latitude
            or self.destination_id.partner_longitude
        ):
            coordinates.append(
                [
                    self.destination_id.partner_latitude,
                    self.destination_id.partner_longitude,
                ]
            )

        return coordinates

    def _get_osrm_route_geometry(self, coordinates):
        """
        Get route geometry from OSRM service.

        Args:
            coordinates: List of [lat, lng] pairs

        Returns:
            List of [lat, lng] points for polyline or None
        """
        self.ensure_one()

        # Check if web_leaflet_routing is available
        RoutingMixin = self.env.get("leaflet.routing.mixin")
        if not RoutingMixin:
            return None

        try:
            # Convert to (lat, lng) tuples for the routing service
            waypoints = [(coord[0], coord[1]) for coord in coordinates]
            result = RoutingMixin.get_route(waypoints)

            if result and result.get("geometry"):
                return result["geometry"]
        except Exception as e:
            _logger.warning("Failed to get OSRM route geometry: %s", e)

        return None

    def action_open_route_map(self):
        """
        Open the order's route in a Leaflet map view.
        """
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": f"Route Map: {self.name}",
            "res_model": "tms.order",
            "view_mode": "leaflet_map",
            "domain": [("id", "=", self.id)],
            "context": {
                "default_origin_id": self.origin_id.id if self.origin_id else False,
            },
        }

    def action_open_stops_map(self):
        """
        Open all delivery stops on a map.
        """
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": f"Delivery Stops: {self.name}",
            "res_model": "tms.order.stop",
            "view_mode": "leaflet_map,list,form",
            "domain": [("order_id", "=", self.id)],
        }
