# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError

ORS_GEOJSON_URL = (
    "https://api.openrouteservice.org/v2/directions/driving-car/geojson"
)
VEHICLE_MODES = {
    "plane": "air",
    "boat": "water",
    "truck": "road",
    "van": "road",
    "bus": "road",
    "car": "road",
}
RAIL_WORDS = ("rail", "train", "wagon", "locomotive")


class TmsOrder(models.Model):
    _inherit = "tms.order"

    def get_live_tracking_coordinates(self):
        """Origin, destination, path, and the latest vehicle position."""
        self.ensure_one()
        origin = self._map_partner_point(self.origin_id)
        destination = self._map_partner_point(self.destination_id)
        return {
            "origin": origin,
            "destination": destination,
            "path": self._map_path(origin, destination),
            "vehicle": self._map_live_vehicle(),
        }

    def _map_partner_point(self, partner):
        if not partner or not (
            partner.partner_latitude or partner.partner_longitude
        ):
            return False
        return {
            "id": partner.id,
            "name": partner.display_name,
            "latitude": partner.partner_latitude,
            "longitude": partner.partner_longitude,
        }

    def _map_transit_mode(self):
        return self._map_mode_for_vehicle(self.vehicle_id)

    @api.model
    def _map_mode_for_vehicle(self, vehicle):
        model = vehicle.model_id
        mode = VEHICLE_MODES.get(model.vehicle_type or "")
        if mode:
            return mode
        category = (model.category_id.name or "").lower()
        if any(word in category for word in RAIL_WORDS):
            return "rail"
        return "road"

    @api.model
    def tms_map_vehicle_positions(self):
        """Latest odometer that carries a position, one pin per vehicle."""
        self.env.cr.execute(
            """
            SELECT DISTINCT ON (log.vehicle_id)
                   log.vehicle_id,
                   log.latitude,
                   log.longitude,
                   log.date
              FROM fleet_vehicle_odometer AS log
             WHERE COALESCE(log.latitude, 0) != 0
                OR COALESCE(log.longitude, 0) != 0
             ORDER BY log.vehicle_id, log.date DESC, log.id DESC
            """
        )
        rows = self.env.cr.fetchall()
        vehicles = self.env["fleet.vehicle"].browse(row[0] for row in rows)
        positions = []
        for vehicle_id, latitude, longitude, moment in rows:
            vehicle = vehicles.browse(vehicle_id)
            positions.append(
                {
                    "id": vehicle.id,
                    "name": vehicle.display_name,
                    "mode": self._map_mode_for_vehicle(vehicle),
                    "latitude": latitude,
                    "longitude": longitude,
                    "date": fields.Datetime.to_string(moment),
                }
            )
        return positions

    def _map_odometers(self, vehicle=None):
        domain = [("vehicle_id", "=", vehicle.id)] if vehicle else []
        return self.env["fleet.vehicle.odometer"].search(
            domain, order="date desc, id desc", limit=2000
        )

    def _map_latest_odometer(self, vehicle):
        if not vehicle:
            return self.env["fleet.vehicle.odometer"]
        logs = self._map_odometers(vehicle)
        return logs.filtered(lambda log: log.latitude or log.longitude)[:1]

    def _map_live_vehicle(self):
        vehicle = self.vehicle_id
        reading = self._map_latest_odometer(vehicle)
        if not vehicle and not reading:
            return False
        return {
            "name": vehicle.display_name if vehicle else "",
            "mode": self._map_transit_mode(),
            "latitude": reading.latitude if reading else False,
            "longitude": reading.longitude if reading else False,
        }

    def _map_path(self, origin, destination):
        straight = self._map_straight_path(origin, destination)
        if not origin or not destination:
            return straight
        route_model = self.env["tms.route"]
        if not hasattr(route_model, "_ors_api_key"):
            return straight
        if not hasattr(route_model, "_ors_request"):
            return straight
        if not route_model._ors_api_key():
            return straight
        try:
            payload = route_model._ors_request(
                "POST",
                ORS_GEOJSON_URL,
                json={
                    "coordinates": [
                        [origin["longitude"], origin["latitude"]],
                        [destination["longitude"], destination["latitude"]],
                    ]
                },
            )
        except UserError:
            return straight
        return self._map_path_from_payload(payload) or straight

    @api.model
    def _map_straight_path(self, origin, destination):
        if not origin or not destination:
            return []
        return [
            [origin["latitude"], origin["longitude"]],
            [destination["latitude"], destination["longitude"]],
        ]

    @api.model
    def _map_path_from_payload(self, payload):
        coordinates = []
        features = payload.get("features") or []
        if features:
            geometry = features[0].get("geometry") or {}
            coordinates = geometry.get("coordinates") or []
        elif payload.get("routes"):
            geometry = payload["routes"][0].get("geometry") or {}
            if isinstance(geometry, dict):
                coordinates = geometry.get("coordinates") or []
        path = []
        for pair in coordinates:
            if len(pair) >= 2:
                path.append([pair[1], pair[0]])
        return path

    @api.model
    def tms_map_open_trips(self):
        trips = self.search(
            [("start_trip", "=", False), ("end_trip", "=", False)]
        )
        return [{"id": trip.id, "name": trip.name} for trip in trips]

    @api.model
    def _map_heatmap_points(self, logs):
        points = []
        for log in logs:
            if not (log.latitude or log.longitude):
                continue
            points.append([log.latitude, log.longitude, 0.6])
        return points

    @api.model
    def tms_map_heatmap(self):
        return self._map_heatmap_points(self._map_odometers())
