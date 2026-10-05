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

    def test_forms_mount_the_map(self):
        partner = self.env.ref("tms_map.view_partner_form_tms_map")
        order = self.env.ref("tms_map.tms_order_view_form_map")
        odometer = self.env.ref("tms_map.fleet_vehicle_odometer_view_form_map")
        self.assertIn('mode="geocoding"', partner.arch)
        self.assertIn('mode="tracking"', order.arch)
        self.assertIn("latitude", odometer.arch)
        self.assertTrue(self.env.ref("tms_map.action_tms_map_dispatch"))
        self.assertTrue(self.env.ref("tms_map.action_tms_map_heatmap"))

    def test_locations_offer_a_map_view(self):
        action = self.env.ref("tms.action_tms_location")
        view = self.env.ref("tms_map.view_res_partner_tms_map")
        self.assertIn("list", action.view_mode)
        self.assertIn("tms_map", action.view_mode)
        self.assertEqual(view.type, "tms_map")
        self.assertIn("partner_latitude", view.arch)
        self.assertIn("tms_map", self.env["ir.ui.view"]._get_view_info())
