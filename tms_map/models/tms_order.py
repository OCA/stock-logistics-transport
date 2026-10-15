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

    tms_vehicle_group_ids = fields.Many2many(
        comodel_name="tms.vehicle.group",
        related="vehicle_id.tms_vehicle_group_ids",
        string="Vehicle Groups",
        groups="tms_map.group_tms_vehicle_group",
    )

    def get_live_tracking_coordinates(self):
        """Origin, destination, path, and the latest vehicle position."""
        self.ensure_one()
        origin = self._map_partner_point(self.origin_id)
        destination = self._map_partner_point(self.destination_id)
        trail = self._map_trip_trail()
        path = trail if len(trail) >= 2 else self._map_path(origin, destination)
        return {
            "origin": origin,
            "destination": destination,
            "path": path,
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
    def _map_motion(self, ignition, speed):
        """Green when on and moving, orange when on and stopped, red otherwise."""
        if ignition == "off":
            return "off"
        if ignition == "on":
            if speed and speed > 0:
                return "moving"
            return "idle"
        return "off"

    @api.model
    def _map_position_rows(self, vehicle_ids=None):
        clause = """
            WHERE COALESCE(log.latitude, 0) != 0
               OR COALESCE(log.longitude, 0) != 0
        """
        params = []
        if vehicle_ids is not None:
            clause += " AND log.vehicle_id IN %s"
            params.append(tuple(vehicle_ids) or (0,))
        odometer = self.env["fleet.vehicle.odometer"]
        telematics = (
            "ignition" in odometer._fields and "speed_known" in odometer._fields
        )
        select = """
            SELECT DISTINCT ON (log.vehicle_id)
                   log.vehicle_id,
                   log.latitude,
                   log.longitude,
                   log.date
        """
        joins = " FROM fleet_vehicle_odometer AS log "
        if telematics:
            select += ", ign.ignition, spd.speed"
            joins += """
                LEFT JOIN LATERAL (
                    SELECT i.ignition
                      FROM fleet_vehicle_odometer AS i
                     WHERE i.vehicle_id = log.vehicle_id
                       AND i.ignition IS NOT NULL
                     ORDER BY i.date DESC, i.id DESC
                     LIMIT 1
                ) AS ign ON TRUE
                LEFT JOIN LATERAL (
                    SELECT s.speed
                      FROM fleet_vehicle_odometer AS s
                     WHERE s.vehicle_id = log.vehicle_id
                       AND s.speed_known
                     ORDER BY s.date DESC, s.id DESC
                     LIMIT 1
                ) AS spd ON TRUE
            """
        self.env.cr.execute(
            select
            + joins
            + clause
            + """
             ORDER BY log.vehicle_id, log.date DESC, log.id DESC
            """,
            params,
        )
        return self.env.cr.fetchall(), telematics

    @api.model
    def tms_map_vehicle_positions(self, vehicle_ids=None):
        """Latest odometer that carries a position, one pin per vehicle."""
        rows, telematics = self._map_position_rows(vehicle_ids)
        vehicles = self.env["fleet.vehicle"].browse(row[0] for row in rows)
        positions = []
        for row in rows:
            if telematics:
                vehicle_id, latitude, longitude, moment, ignition, speed = row
                motion = self._map_motion(ignition, speed)
            else:
                vehicle_id, latitude, longitude, moment = row
                motion = "off"
            vehicle = vehicles.browse(vehicle_id)
            positions.append(
                {
                    "id": vehicle.id,
                    "name": vehicle.display_name,
                    "mode": self._map_mode_for_vehicle(vehicle),
                    "latitude": latitude,
                    "longitude": longitude,
                    "date": fields.Datetime.to_string(moment),
                    "motion": motion,
                }
            )
        return positions

    @api.model
    def tms_map_fleet(self, team_id=False):
        """Vehicles of one team, with the latest position when it exists."""
        if not team_id:
            return []
        vehicles = self.env["fleet.vehicle"].search(
            [("tms_team_id", "=", team_id)], order="name, id"
        )
        positions = {
            row["id"]: row for row in self.tms_map_vehicle_positions(vehicles.ids)
        }
        rows = []
        for vehicle in vehicles:
            position = positions.get(vehicle.id, {})
            driver = vehicle.tms_driver_id
            rows.append(
                {
                    "id": vehicle.id,
                    "name": vehicle.display_name,
                    "driver": driver.display_name if driver else False,
                    "mode": position.get("mode")
                    or self._map_mode_for_vehicle(vehicle),
                    "motion": position.get("motion") or "off",
                    "latitude": position.get("latitude") or False,
                    "longitude": position.get("longitude") or False,
                    "date": position.get("date") or False,
                }
            )
        return rows

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

    def _map_trip_trail(self):
        """Odometer positions between the actual start and end of the trip."""
        self.ensure_one()
        vehicle = self.vehicle_id
        start = self.date_start
        if not vehicle or not start:
            return []
        domain = [
            ("vehicle_id", "=", vehicle.id),
            ("date", ">=", start),
        ]
        if self.date_end:
            domain.append(("date", "<=", self.date_end))
        logs = self.env["fleet.vehicle.odometer"].search(domain, order="date, id")
        return [
            [log.latitude, log.longitude]
            for log in logs
            if log.latitude or log.longitude
        ]

    def _map_live_vehicle(self):
        vehicle = self.vehicle_id
        if not vehicle:
            return False
        positions = self.tms_map_vehicle_positions([vehicle.id])
        position = positions[0] if positions else {}
        return {
            "name": vehicle.display_name,
            "mode": self._map_transit_mode(),
            "latitude": position.get("latitude") or False,
            "longitude": position.get("longitude") or False,
            "motion": position.get("motion") or "off",
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

    def _map_history_row(self):
        self.ensure_one()
        start = self.date_start or self.scheduled_date_start
        end = self.date_end or self.scheduled_date_end
        distance = 0.0
        if self.odometer_end and self.odometer_start:
            distance = self.odometer_end - self.odometer_start
        return {
            "id": self.id,
            "name": self.name,
            "vehicle": self.vehicle_id.display_name,
            "origin": self.origin_id.display_name or "",
            "destination": self.destination_id.display_name or "",
            "date_start": fields.Datetime.to_string(start) if start else False,
            "date_end": fields.Datetime.to_string(end) if end else False,
            "distance": round(distance, 1),
        }

    @api.model
    def tms_map_trip_history(self, vehicle_id=False, limit=80):
        """Recent trips, optionally limited to one vehicle."""
        domain = [("vehicle_id", "!=", False)]
        if vehicle_id:
            domain.append(("vehicle_id", "=", vehicle_id))
        trips = self.search(domain, order="date_start desc, id desc", limit=limit)
        return [trip._map_history_row() for trip in trips]

    def tms_map_history_tracks(self):
        """Path and stops for the trips selected on the history map."""
        tracks = []
        for trip in self:
            payload = trip.get_live_tracking_coordinates()
            payload["id"] = trip.id
            payload["name"] = trip.name
            tracks.append(payload)
        return tracks

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
    def tms_map_heatmap(self, vehicle_ids=None):
        logs = self._map_odometers()
        if vehicle_ids is not None:
            allowed = set(vehicle_ids)
            logs = logs.filtered(lambda log: log.vehicle_id.id in allowed)
        return self._map_heatmap_points(logs)
