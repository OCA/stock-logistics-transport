# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class _Delay:
    def __init__(self, record, bucket):
        self.record = record
        self.bucket = bucket

    def _job_compute_route(self):
        self.bucket["jobs"] = self.bucket.get("jobs", 0) + 1
        self.bucket["route"] = self.record


class TestRouting(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.km = cls.env.ref("uom.product_uom_km")
        cls.hour = cls.env.ref("uom.product_uom_hour")
        cls.origin = cls.env["res.partner"].create(
            {
                "name": "Origin yard",
                "tms_location": True,
                "partner_latitude": 29.76,
                "partner_longitude": -95.36,
            }
        )
        cls.stop = cls.env["res.partner"].create(
            {
                "name": "Mid stop",
                "tms_location": True,
                "partner_latitude": 30.26,
                "partner_longitude": -97.74,
            }
        )
        cls.destination = cls.env["res.partner"].create(
            {
                "name": "Destination yard",
                "tms_location": True,
                "partner_latitude": 32.77,
                "partner_longitude": -96.79,
            }
        )
        cls.route = cls.env["tms.route"].create(
            {
                "name": "Houston to Dallas",
                "origin_location_id": cls.origin.id,
                "destination_location_id": cls.destination.id,
                "distance_uom": cls.km.id,
                "estimated_time_uom": cls.hour.id,
            }
        )

    def _select_provider(self, route, provider):
        field = type(route)._fields["routing_provider"]
        selection = field.selection
        field.selection = [(provider, provider)]
        self.addCleanup(setattr, field, "selection", selection)
        route.routing_provider = provider

    def test_points_follow_stop_sequence_and_stop_coordinates(self):
        later = self.env["tms.route.stop"].create(
            {"route_id": self.route.id, "sequence": 20, "location_id": self.stop.id}
        )
        earlier = self.env["tms.route.stop"].create(
            {
                "route_id": self.route.id,
                "sequence": 5,
                "location_id": self.origin.id,
                "latitude": 29.8,
                "longitude": -95.4,
            }
        )
        points = self.route._routing_points()
        self.assertEqual(
            [point["partner"] for point in points],
            [self.origin, self.origin, self.stop, self.destination],
        )
        self.assertEqual(points[1]["latitude"], earlier.latitude)
        self.assertEqual(points[2]["latitude"], self.stop.partner_latitude)
        self.assertEqual(later.sequence, 20)

    def test_measures_convert_meters_and_seconds(self):
        self.route.distance_uom = False
        self.route.estimated_time_uom = False
        measures = self.route._routing_measures(2000, 1800)
        self.assertEqual(measures["distance_uom"], self.km)
        self.assertAlmostEqual(measures["distance"], 2.0)
        self.assertEqual(measures["duration_uom"], self.hour)
        self.assertAlmostEqual(measures["duration"], 0.5)

    def test_compute_requires_a_provider(self):
        with self.assertRaises(UserError):
            self.route._compute_route_path()

    def test_compute_reports_a_missing_handler(self):
        self._select_provider(self.route, "ghost")
        with self.assertRaises(UserError):
            self.route._compute_route_path()

    def test_compute_calls_the_provider_handler(self):
        self._select_provider(self.route, "fake")

        def _compute_route_path_fake(route):
            return route._routing_measures(1000, 3600)

        with patch.object(
            type(self.route),
            "_compute_route_path_fake",
            _compute_route_path_fake,
            create=True,
        ):
            measures = self.route._compute_route_path()
        self.assertAlmostEqual(measures["distance"], 1.0)
        self.assertAlmostEqual(measures["duration"], 1.0)

    def test_job_stores_the_path_and_an_error(self):
        self._select_provider(self.route, "fake")

        def _compute_route_path_fake(route):
            return route._routing_measures(5000, 7200)

        with patch.object(
            type(self.route),
            "_compute_route_path_fake",
            _compute_route_path_fake,
            create=True,
        ):
            self.route._job_compute_route()
        self.assertEqual(self.route.routing_state, "done")
        self.assertAlmostEqual(self.route.distance, 5.0)
        self.assertAlmostEqual(self.route.estimated_time, 2.0)
        self.assertFalse(self.route.routing_error)

        def _fail(route):
            raise UserError(route.env._("Provider down"))

        with patch.object(
            type(self.route), "_compute_route_path_fake", _fail, create=True
        ):
            self.route._job_compute_route()
        self.assertEqual(self.route.routing_state, "error")
        self.assertIn("Provider down", self.route.routing_error)

    def test_action_queues_the_job(self):
        self._select_provider(self.route, "fake")
        bucket = {}

        def _with_delay(record, *args, **kwargs):
            bucket["channel"] = kwargs.get("channel")
            bucket["identity_key"] = kwargs.get("identity_key")
            return _Delay(record, bucket)

        with patch.object(type(self.route), "with_delay", _with_delay, create=True):
            self.assertTrue(self.route.action_compute_route())
        self.assertEqual(self.route.routing_state, "pending")
        self.assertEqual(bucket["channel"], "root.routing")
        self.assertEqual(bucket["identity_key"], f"tms.route.{self.route.id}")
        self.assertEqual(bucket["jobs"], 1)

    def test_action_requires_a_provider(self):
        with self.assertRaises(UserError):
            self.route.action_compute_route()
