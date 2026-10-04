# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import requests

from odoo import api, models
from odoo.exceptions import UserError

ORS_DIRECTIONS_URL = "https://api.openrouteservice.org/v2/directions/driving-car/json"
ORS_GEOCODE_URL = "https://api.openrouteservice.org/geocode/search"


class TmsRoute(models.Model):
    _inherit = "tms.route"

    @api.model
    def _selection_routing_provider(self):
        return super()._selection_routing_provider() + [("ors", "OpenRouteService")]

    def _ors_api_key(self):
        return (
            self.env["ir.config_parameter"].sudo().get_param("tms_routing_ors.api_key")
        )

    def _ors_request(self, method, url, **kwargs):
        key = self._ors_api_key()
        if not key:
            raise UserError(
                self.env._("Set the OpenRouteService API key in Transport settings.")
            )
        response = requests.request(
            method,
            url,
            headers={"Authorization": key},
            timeout=30,
            **kwargs,
        )
        if response.status_code >= 400:
            raise UserError(
                self.env._(
                    "OpenRouteService refused the request (%(status)s).",
                    status=response.status_code,
                )
            )
        return response.json()

    def _ors_geocode(self, partner):
        text = (partner.contact_address or partner.display_name or "").strip()
        if not text:
            raise UserError(
                self.env._(
                    "OpenRouteService needs an address for %(name)s.",
                    name=partner.display_name or "",
                )
            )
        payload = self._ors_request(
            "GET",
            ORS_GEOCODE_URL,
            params={"text": text, "size": 1},
        )
        features = payload.get("features") or []
        if not features:
            raise UserError(
                self.env._(
                    "OpenRouteService could not locate %(name)s.",
                    name=partner.display_name,
                )
            )
        longitude, latitude = features[0]["geometry"]["coordinates"]
        return latitude, longitude

    def _ors_lat_lon(self, point):
        if point["latitude"] or point["longitude"]:
            return point["latitude"], point["longitude"]
        return self._ors_geocode(point["partner"])

    def _compute_route_path_ors(self):
        self.ensure_one()
        coordinates = []
        for point in self._routing_points():
            latitude, longitude = self._ors_lat_lon(point)
            coordinates.append([longitude, latitude])
        if len(coordinates) < 2:
            raise UserError(self.env._("A route needs an origin and a destination."))
        body = {"coordinates": coordinates}
        if self.avoid_tolls:
            body["options"] = {"avoid_features": ["tollways"]}
        payload = self._ors_request("POST", ORS_DIRECTIONS_URL, json=body)
        routes = payload.get("routes") or []
        if not routes:
            raise UserError(self.env._("OpenRouteService returned no path."))
        summary = routes[0]["summary"]
        return self._routing_measures(summary["distance"], summary["duration"])
