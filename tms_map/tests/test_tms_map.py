# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import date
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase


class TestTmsMap(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.origin = cls.env["res.partner"].create(
            {
                "name": "Map Origin",
                "tms_location": True,
                "partner_latitude": 29.76,
                "partner_longitude": -95.36,
            }
        )
        cls.destination = cls.env["res.partner"].create(
            {
                "name": "Map Destination",
                "tms_location": True,
                "partner_latitude": 32.77,
                "partner_longitude": -96.79,
            }
        )
        cls.brand = cls.env["fleet.vehicle.model.brand"].create({"name": "Map"})
        cls.model = cls.env["fleet.vehicle.model"].create(
            {"name": "Map truck", "brand_id": cls.brand.id, "vehicle_type": "truck"}
        )
        cls.vehicle = cls.env["fleet.vehicle"].create(
            {
                "name": "Map truck",
                "model_id": cls.model.id,
                "odometer_unit": "kilometers",
                "operation": "cargo",
            }
        )
        cls.order = cls.env["tms.order"].create(
            {
                "name": "Map trip",
                "origin_id": cls.origin.id,
                "destination_id": cls.destination.id,
                "vehicle_id": cls.vehicle.id,
            }
        )

    def test_partner_pin_is_stored(self):
        self.origin.tms_map_set_coordinates(30.0, -90.0)
        self.assertEqual(self.origin.partner_latitude, 30.0)
        self.assertEqual(self.origin.partner_longitude, -90.0)

    def test_transport_locations_are_shared_by_every_map(self):
        self.origin.tms_map_shape = "point"
        hidden = self.env["res.partner"].create(
            {
                "name": "Not a location",
                "partner_latitude": 1.0,
                "partner_longitude": 2.0,
                "tms_map_shape": "point",
            }
        )
        self.destination.tms_map_set_geofence(
            [[10.0, 10.0], [11.0, 10.0], [11.0, 11.0]]
        )
        rows = {
            row["id"]: row for row in self.env["res.partner"].tms_map_locations()
        }
        self.assertEqual(rows[self.origin.id]["shape"], "point")
        self.assertEqual(rows[self.origin.id]["latitude"], 29.76)
        self.assertEqual(rows[self.destination.id]["shape"], "area")
        self.assertEqual(len(rows[self.destination.id]["perimeter"]), 3)
        self.assertNotIn(hidden.id, rows)

    def test_demo_location_perimeters_are_areas(self):
        from odoo.addons.tms_map.demo.location_perimeters import PERIMETERS

        self.assertEqual(len(PERIMETERS), 9)
        for corners in PERIMETERS.values():
            self.assertGreaterEqual(len(corners), 3)
        self.origin.tms_map_set_geofence(PERIMETERS["tms.demo_location_1"])
        self.assertEqual(self.origin.tms_map_shape, "area")
        self.assertEqual(len(self.origin.tms_geofence), 4)
        self.env["res.partner"]._demo_apply_location_perimeters()

    def test_geofence_stores_the_perimeter(self):
        corners = [[19.4, -99.2], [19.5, -99.2], [19.45, -99.1]]
        self.origin.tms_map_set_geofence(corners)
        self.assertEqual(self.origin.tms_map_shape, "area")
        self.assertEqual(len(self.origin.tms_geofence), 3)
        self.assertAlmostEqual(self.origin.partner_latitude, 19.45, places=5)
        self.assertAlmostEqual(self.origin.partner_longitude, -99.1666667, places=5)
        with self.assertRaises(UserError):
            self.origin.tms_map_set_geofence([[1.0, 2.0], [3.0, 4.0]])
        self.origin.tms_map_set_geofence([])
        self.assertFalse(self.origin.tms_geofence)
        form = self.env.ref("tms_map.view_partner_form_tms_map")
        view = self.env.ref("tms_map.view_res_partner_tms_map")
        self.assertIn("tms_geofence", form.arch)
        self.assertIn("perimeter", view.arch)

    def test_tracking_uses_a_straight_path_without_a_router(self):
        payload = self.order.get_live_tracking_coordinates()
        self.assertEqual(payload["origin"]["name"], "Map Origin")
        self.assertEqual(payload["destination"]["latitude"], 32.77)
        self.assertEqual(
            payload["path"],
            [[29.76, -95.36], [32.77, -96.79]],
        )
        self.assertEqual(payload["vehicle"]["mode"], "road")
        self.assertFalse(payload["vehicle"]["latitude"])

    def test_tracking_without_coordinates_has_no_path(self):
        self.origin.write({"partner_latitude": 0, "partner_longitude": 0})
        self.destination.write({"partner_latitude": 0, "partner_longitude": 0})
        payload = self.order.get_live_tracking_coordinates()
        self.assertFalse(payload["origin"])
        self.assertFalse(payload["destination"])
        self.assertEqual(payload["path"], [])

    def test_vehicle_mode_follows_the_model(self):
        self.model.vehicle_type = "plane"
        self.assertEqual(self.order._map_transit_mode(), "air")
        self.model.vehicle_type = "boat"
        self.assertEqual(self.order._map_transit_mode(), "water")
        category = self.env["fleet.vehicle.model.category"].create(
            {"name": "Locomotive"}
        )
        self.model.write({"vehicle_type": "bike", "category_id": category.id})
        self.assertEqual(self.order._map_transit_mode(), "rail")
        self.model.category_id = False
        self.assertEqual(self.order._map_transit_mode(), "road")

    def test_live_position_is_the_latest_odometer(self):
        self.env["fleet.vehicle.odometer"].create(
            {
                "vehicle_id": self.vehicle.id,
                "value": 100,
                "date": date(2026, 1, 1),
                "latitude": 25.0,
                "longitude": -100.0,
            }
        )
        self.env["fleet.vehicle.odometer"].create(
            {
                "vehicle_id": self.vehicle.id,
                "value": 110,
                "date": date(2026, 1, 2),
                "latitude": 26.0,
                "longitude": -101.0,
            }
        )
        self.env["fleet.vehicle.odometer"].create(
            {
                "vehicle_id": self.vehicle.id,
                "value": 120,
                "date": date(2026, 1, 3),
            }
        )
        payload = self.order.get_live_tracking_coordinates()
        self.assertEqual(payload["vehicle"]["latitude"], 26.0)
        self.assertEqual(payload["vehicle"]["longitude"], -101.0)

    def test_dispatch_uses_the_latest_position_of_each_vehicle(self):
        self.env["fleet.vehicle.odometer"].create(
            {
                "vehicle_id": self.vehicle.id,
                "value": 100,
                "date": fields.Datetime.to_datetime("2026-01-01 08:00:00"),
                "latitude": 25.0,
                "longitude": -100.0,
            }
        )
        self.env["fleet.vehicle.odometer"].create(
            {
                "vehicle_id": self.vehicle.id,
                "value": 110,
                "date": fields.Datetime.to_datetime("2026-01-02 08:00:00"),
                "latitude": 26.0,
                "longitude": -101.0,
            }
        )
        self.env["fleet.vehicle.odometer"].create(
            {
                "vehicle_id": self.vehicle.id,
                "value": 120,
                "date": fields.Datetime.to_datetime("2026-01-03 08:00:00"),
            }
        )
        other = self.env["fleet.vehicle"].create(
            {
                "name": "Map van",
                "model_id": self.model.id,
                "odometer_unit": "kilometers",
                "operation": "cargo",
            }
        )
        self.env["fleet.vehicle.odometer"].create(
            {
                "vehicle_id": other.id,
                "value": 10,
                "date": fields.Datetime.to_datetime("2026-02-01 08:00:00"),
                "latitude": 19.4,
                "longitude": -99.1,
            }
        )
        idle = self.env["fleet.vehicle"].create(
            {
                "name": "Map idle",
                "model_id": self.model.id,
                "odometer_unit": "kilometers",
                "operation": "cargo",
            }
        )
        positions = {
            row["id"]: row
            for row in self.env["tms.order"].tms_map_vehicle_positions()
        }
        self.assertEqual(positions[self.vehicle.id]["latitude"], 26.0)
        self.assertEqual(positions[self.vehicle.id]["longitude"], -101.0)
        self.assertEqual(positions[self.vehicle.id]["mode"], "road")
        self.assertEqual(positions[other.id]["latitude"], 19.4)
        self.assertNotIn(idle.id, positions)

    def test_a_trip_without_a_vehicle_has_no_live_pin(self):
        self.order.vehicle_id = False
        payload = self.order.get_live_tracking_coordinates()
        self.assertFalse(payload["vehicle"])

    def test_openrouteservice_path_replaces_the_straight_line(self):
        payload = {
            "features": [
                {
                    "geometry": {
                        "coordinates": [
                            [-95.36, 29.76],
                            [-96.0, 31.0],
                            [-96.79, 32.77],
                        ]
                    }
                }
            ]
        }
        route = type(self.env["tms.route"])
        with (
            patch.object(route, "_ors_api_key", lambda self: "key", create=True),
            patch.object(
                route,
                "_ors_request",
                lambda self, *args, **kwargs: payload,
                create=True,
            ),
        ):
            path = self.order._map_path(
                self.order._map_partner_point(self.origin),
                self.order._map_partner_point(self.destination),
            )
        self.assertEqual(path[1], [31.0, -96.0])

    def test_a_router_error_keeps_the_straight_line(self):
        route = type(self.env["tms.route"])

        def fail(self, *args, **kwargs):
            raise UserError("down")

        with (
            patch.object(route, "_ors_api_key", lambda self: "key", create=True),
            patch.object(route, "_ors_request", fail, create=True),
        ):
            path = self.order._map_path(
                {"latitude": 1.0, "longitude": 2.0},
                {"latitude": 3.0, "longitude": 4.0},
            )
        self.assertEqual(path, [[1.0, 2.0], [3.0, 4.0]])

    def test_route_geometry_is_read_from_either_payload_shape(self):
        order = self.env["tms.order"]
        geojson = order._map_path_from_payload(
            {"features": [{"geometry": {"coordinates": [[10, 1], [11, 2]]}}]}
        )
        routes = order._map_path_from_payload(
            {"routes": [{"geometry": {"coordinates": [[8, 3]]}}]}
        )
        empty = order._map_path_from_payload({"features": []})
        short = order._map_path_from_payload(
            {"routes": [{"geometry": {"coordinates": [[9]]}}]}
        )
        self.assertEqual(geojson, [[1, 10], [2, 11]])
        self.assertEqual(routes, [[3, 8]])
        self.assertEqual(empty, [])
        self.assertEqual(short, [])

    def test_heatmap_plots_odometers_that_have_a_position(self):
        self.env["fleet.vehicle.odometer"].create(
            {
                "vehicle_id": self.vehicle.id,
                "value": 1,
                "latitude": 19.4,
                "longitude": -99.1,
            }
        )
        self.env["fleet.vehicle.odometer"].create(
            {"vehicle_id": self.vehicle.id, "value": 2}
        )
        points = self.env["tms.order"].tms_map_heatmap()
        self.assertIn([19.4, -99.1, 0.6], points)
        self.assertFalse(any(point[0] == 0 and point[1] == 0 for point in points))
        narrowed = self.env["tms.order"].tms_map_heatmap([self.vehicle.id])
        self.assertIn([19.4, -99.1, 0.6], narrowed)
        self.assertEqual(self.env["tms.order"].tms_map_heatmap([]), [])

    def test_unassigned_cargo_clusters_by_origin(self):
        first = self.env["tms.cargo"].create(
            {
                "name": "Map box",
                "order_id": self.order.id,
                "state": "unassigned",
            }
        )
        second = self.env["tms.cargo"].create(
            {
                "name": "Map pallet",
                "order_id": self.order.id,
                "state": "unassigned",
            }
        )
        loose = self.env["tms.cargo"].create(
            {"name": "Map loose", "state": "unassigned"}
        )
        clusters = self.env["tms.cargo"].tms_map_unassigned_clusters()
        located = next(
            cluster
            for cluster in clusters
            if any(line["id"] == first.id for line in cluster["cargo"])
        )
        self.assertEqual(located["partner_id"], self.origin.id)
        self.assertEqual(located["latitude"], 29.76)
        located_ids = {line["id"] for line in located["cargo"]}
        self.assertTrue({first.id, second.id} <= located_ids)
        missing = next(
            cluster
            for cluster in clusters
            if any(line["id"] == loose.id for line in cluster["cargo"])
        )
        self.assertFalse(missing["partner_id"])
        self.assertEqual(missing["name"], "No location")

    def test_assign_places_unassigned_cargo_on_an_open_trip(self):
        cargo = self.env["tms.cargo"].create(
            {"name": "Map assign", "state": "unassigned"}
        )
        other = self.env["tms.order"].create({"name": "Map other"})
        cargo.tms_map_assign(other.id)
        self.assertEqual(cargo.order_id, other)
        self.assertEqual(cargo.state, "planned")
        open_ids = {trip["id"] for trip in self.env["tms.order"].tms_map_open_trips()}
        self.assertIn(other.id, open_ids)
        other.start_trip = True
        open_ids = {trip["id"] for trip in self.env["tms.order"].tms_map_open_trips()}
        self.assertNotIn(other.id, open_ids)

    def test_assign_refuses_a_started_trip_and_planned_cargo(self):
        cargo = self.env["tms.cargo"].create(
            {"name": "Map started", "state": "unassigned"}
        )
        self.order.start_trip = True
        with self.assertRaises(UserError):
            cargo.tms_map_assign(self.order.id)
        cargo.tms_map_assign(self.env["tms.order"].create({"name": "Map open"}).id)
        with self.assertRaises(UserError):
            cargo.tms_map_assign(self.env["tms.order"].create({"name": "Map later"}).id)

    def test_assign_is_limited_to_transport_users(self):
        cargo = self.env["tms.cargo"].create(
            {"name": "Map locked", "state": "unassigned"}
        )
        user = self.env["res.users"].create(
            {
                "name": "Map outsider",
                "login": "tms_map_outsider",
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        with self.assertRaises(AccessError):
            cargo.with_user(user).tms_map_assign(self.order.id)

    def test_team_dashboard_opens_the_last_vehicle_locations(self):
        team = self.env["tms.team"].create(
            {"name": "Map team", "vehicle_ids": [(6, 0, [self.vehicle.id])]}
        )
        self.env["fleet.vehicle.odometer"].create(
            {
                "vehicle_id": self.vehicle.id,
                "value": 40,
                "date": fields.Datetime.to_datetime("2026-04-01 08:00:00"),
                "latitude": 20.1,
                "longitude": -100.2,
            }
        )
        self.env["fleet.vehicle.odometer"].create(
            {
                "vehicle_id": self.vehicle.id,
                "value": 50,
                "date": fields.Datetime.to_datetime("2026-04-02 08:00:00"),
                "latitude": 21.3,
                "longitude": -101.4,
            }
        )
        self.assertEqual(self.vehicle.tms_last_latitude, 21.3)
        self.assertEqual(self.vehicle.tms_last_longitude, -101.4)
        idle = self.env["fleet.vehicle"].create(
            {
                "name": "Map parked",
                "model_id": self.model.id,
                "odometer_unit": "kilometers",
                "operation": "cargo",
            }
        )
        self.assertFalse(idle.tms_last_latitude)
        self.assertFalse(idle.tms_last_longitude)
        positions = self.env["tms.order"].tms_map_vehicle_positions([self.vehicle.id])
        self.assertEqual([row["id"] for row in positions], [self.vehicle.id])
        action = self.env.ref("tms_map.action_tms_map_fleet")
        self.assertEqual(action._name, "ir.actions.client")
        self.assertEqual(action.tag, "tms_map")
        self.assertIn("fleet", action.context)
        view = self.env.ref("tms_map.fleet_vehicle_view_tms_map")
        self.assertEqual(view.type, "tms_map")
        self.assertIn("tms_last_latitude", view.arch)
        self.assertIn("tms_map_mode", view.arch)
        self.assertIn("tms_motion", view.arch)
        self.assertEqual(self.vehicle.tms_map_mode, "road")
        kanban = self.env["tms.team"].get_view(view_id=False, view_type="kanban")
        self.assertIn(str(action.id), kanban["arch"])
        self.assertEqual(team.vehicle_count, 1)

    def test_pin_status_follows_ignition_and_speed(self):
        order = self.env["tms.order"]
        self.assertEqual(order._map_motion("on", 30), "moving")
        self.assertEqual(order._map_motion("on", 0), "idle")
        self.assertEqual(order._map_motion("off", 80), "off")
        self.assertEqual(order._map_motion(False, 80), "off")
        self.model.vehicle_type = "boat"
        self.assertEqual(self.vehicle.tms_map_mode, "water")
        self.model.vehicle_type = "plane"
        self.assertEqual(self.vehicle.tms_map_mode, "air")
        if "ignition" not in self.env["fleet.vehicle.odometer"]._fields:
            return
        self.env["fleet.vehicle.odometer"].create(
            {
                "vehicle_id": self.vehicle.id,
                "value": 10,
                "date": fields.Datetime.to_datetime("2026-06-01 08:00:00"),
                "latitude": 19.0,
                "longitude": -99.0,
                "ignition": "on",
            }
        )
        self.env["fleet.vehicle.odometer"].create(
            {
                "vehicle_id": self.vehicle.id,
                "value": 11,
                "date": fields.Datetime.to_datetime("2026-06-01 08:05:00"),
                "latitude": 19.1,
                "longitude": -99.1,
                "speed": 45,
                "speed_known": True,
            }
        )
        self.assertEqual(self.vehicle.tms_motion, "moving")
        positions = order.tms_map_vehicle_positions([self.vehicle.id])
        self.assertEqual(positions[0]["motion"], "moving")
        self.assertEqual(positions[0]["mode"], "air")
        self.env["fleet.vehicle.odometer"].create(
            {
                "vehicle_id": self.vehicle.id,
                "value": 12,
                "date": fields.Datetime.to_datetime("2026-06-01 08:10:00"),
                "latitude": 19.2,
                "longitude": -99.2,
                "speed": 0,
                "speed_known": True,
            }
        )
        self.assertEqual(self.vehicle.tms_motion, "idle")
        self.env["fleet.vehicle.odometer"].create(
            {
                "vehicle_id": self.vehicle.id,
                "value": 13,
                "date": fields.Datetime.to_datetime("2026-06-01 08:10:00"),
                "latitude": 19.2,
                "longitude": -99.2,
                "ignition": "off",
            }
        )
        self.assertEqual(self.vehicle.tms_motion, "off")
        live = self.order._map_live_vehicle()
        self.assertEqual(live["motion"], "off")
        self.assertEqual(live["mode"], "air")

    def test_forms_mount_the_map(self):
        partner = self.env.ref("tms_map.view_partner_form_tms_map")
        order = self.env.ref("tms_map.tms_order_view_form_map")
        odometer = self.env.ref("tms_map.fleet_vehicle_odometer_view_form_map")
        self.assertIn('mode="geocoding"', partner.arch)
        self.assertIn('mode="tracking"', order.arch)
        self.assertIn("latitude", odometer.arch)
        self.assertTrue(self.env.ref("tms_map.action_tms_map_dispatch"))
        self.assertTrue(self.env.ref("tms_map.action_tms_map_heatmap"))
        history = self.env.ref("tms_map.action_tms_map_history")
        menu = self.env.ref("tms_map.menu_tms_map_history")
        self.assertEqual(history.tag, "tms_map")
        self.assertIn("history", history.context)
        self.assertEqual(menu.action.id, history.id)
        form = self.env["fleet.vehicle"].get_view(view_type="form")
        self.assertIn("tms_trip_count", form["arch"])
        self.assertIn(str(history.id), form["arch"])

    def test_live_fleet_lists_one_team(self):
        driver = self.env["tms.driver"].create({"name": "Map driver"})
        self.vehicle.tms_driver_id = driver
        other = self.env["fleet.vehicle"].create(
            {
                "name": "Map other",
                "model_id": self.model.id,
                "odometer_unit": "kilometers",
                "operation": "cargo",
            }
        )
        parked = self.env["fleet.vehicle"].create(
            {
                "name": "Map parked",
                "model_id": self.model.id,
                "odometer_unit": "kilometers",
                "operation": "cargo",
            }
        )
        team = self.env["tms.team"].create(
            {
                "name": "Fleet team",
                "vehicle_ids": [(6, 0, [self.vehicle.id, parked.id])],
            }
        )
        self.env["fleet.vehicle.odometer"].create(
            {
                "vehicle_id": self.vehicle.id,
                "value": 10,
                "date": fields.Datetime.to_datetime("2026-07-01 08:00:00"),
                "latitude": 19.4,
                "longitude": -99.1,
            }
        )
        rows = {row["id"]: row for row in self.env["tms.order"].tms_map_fleet(team.id)}
        self.assertEqual(set(rows), {self.vehicle.id, parked.id})
        self.assertNotIn(other.id, rows)
        self.assertEqual(rows[self.vehicle.id]["driver"], "Map driver")
        self.assertEqual(rows[self.vehicle.id]["latitude"], 19.4)
        self.assertFalse(rows[parked.id]["latitude"])
        self.assertFalse(self.env["tms.order"].tms_map_fleet(False))

    def test_trip_history_follows_the_vehicle_and_the_trail(self):
        other = self.env["fleet.vehicle"].create(
            {
                "name": "History other",
                "model_id": self.model.id,
                "odometer_unit": "kilometers",
                "operation": "cargo",
            }
        )
        other_trip = self.env["tms.order"].create(
            {
                "name": "Other map trip",
                "origin_id": self.origin.id,
                "destination_id": self.destination.id,
                "vehicle_id": other.id,
            }
        )
        start = self.env["fleet.vehicle.odometer"].create(
            {
                "vehicle_id": self.vehicle.id,
                "value": 100,
                "date": fields.Datetime.to_datetime("2026-05-01 08:30:00"),
                "latitude": 30.0,
                "longitude": -95.0,
            }
        )
        end = self.env["fleet.vehicle.odometer"].create(
            {
                "vehicle_id": self.vehicle.id,
                "value": 180,
                "date": fields.Datetime.to_datetime("2026-05-01 11:00:00"),
                "latitude": 31.0,
                "longitude": -96.0,
            }
        )
        self.order.write(
            {
                "date_start": fields.Datetime.to_datetime("2026-05-01 08:00:00"),
                "duration": 6,
                "odometer_start_id": start.id,
                "odometer_end_id": end.id,
            }
        )
        payload = self.order.get_live_tracking_coordinates()
        self.assertEqual(payload["path"], [[30.0, -95.0], [31.0, -96.0]])
        history = self.env["tms.order"].tms_map_trip_history(self.vehicle.id)
        ids = [row["id"] for row in history]
        self.assertIn(self.order.id, ids)
        self.assertNotIn(other_trip.id, ids)
        row = next(item for item in history if item["id"] == self.order.id)
        self.assertEqual(row["distance"], 80)
        self.assertEqual(row["origin"], "Map Origin")
        self.assertEqual(self.vehicle.tms_trip_count, 1)
        tracks = self.order.tms_map_history_tracks()
        self.assertEqual(tracks[0]["id"], self.order.id)
        self.assertEqual(tracks[0]["path"][0], [30.0, -95.0])
        everyone = self.env["tms.order"].tms_map_trip_history()
        self.assertIn(other_trip.id, [item["id"] for item in everyone])

    def test_locations_offer_a_map_view(self):
        action = self.env.ref("tms.action_tms_location")
        view = self.env.ref("tms_map.view_res_partner_tms_map")
        self.assertIn("list", action.view_mode)
        self.assertIn("tms_map", action.view_mode)
        self.assertEqual(view.type, "tms_map")
        self.assertIn("partner_latitude", view.arch)
        self.assertIn("tms_map", self.env["ir.ui.view"]._get_view_info())

    def test_vehicle_groups_are_optional(self):
        group = self.env["tms.vehicle.group"].create(
            {"name": "North", "vehicle_ids": [(4, self.vehicle.id)]}
        )
        self.assertEqual(self.vehicle.tms_vehicle_group_ids, group)
        self.assertEqual(self.order.tms_vehicle_group_ids, group)
        setting = self.env["res.config.settings"].create({})
        self.assertFalse(setting.group_tms_vehicle_group)
        menu = self.env.ref("tms_map.menu_tms_vehicle_group")
        self.assertEqual(menu.parent_id, self.env.ref("tms.config"))
        self.assertEqual(self.vehicle.tms_motion, "off")
