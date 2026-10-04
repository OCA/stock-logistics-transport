# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase

from odoo.addons.tms_routing_ors.models.tms_route import (
    ORS_DIRECTIONS_URL,
    ORS_GEOCODE_URL,
)


class _Response:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


class TestOpenRouteService(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.origin = cls.env["res.partner"].create(
            {
                "name": "Origin yard",
                "tms_location": True,
                "partner_latitude": 29.76,
                "partner_longitude": -95.36,
            }
        )
        cls.destination = cls.env["res.partner"].create(
            {
                "name": "Destination yard",
                "tms_location": True,
                "street": "1 Main",
                "city": "Dallas",
            }
        )
        cls.route = cls.env["tms.route"].create(
            {
                "name": "Houston to Dallas",
                "origin_location_id": cls.origin.id,
                "destination_location_id": cls.destination.id,
                "routing_provider": "ors",
                "distance_uom": cls.env.ref("uom.product_uom_km").id,
                "estimated_time_uom": cls.env.ref("uom.product_uom_hour").id,
            }
        )
        cls.env["ir.config_parameter"].sudo().set_param(
            "tms_routing_ors.api_key", "test-key"
        )

    def _requests(self, payloads):
        calls = []

        def _request(method, url, headers=None, timeout=None, **kwargs):
            calls.append(
                {
                    "method": method,
                    "url": url,
                    "headers": headers,
                    "timeout": timeout,
                    "kwargs": kwargs,
                }
            )
            status, payload = payloads.pop(0)
            return _Response(payload, status)

        return calls, _request

    def test_directions_use_coordinates_and_geocode_the_destination(self):
        calls, _request = self._requests(
            [
                (
                    200,
                    {
                        "features": [
                            {"geometry": {"coordinates": [-96.79, 32.77]}},
                        ]
                    },
                ),
                (
                    200,
                    {"routes": [{"summary": {"distance": 360000, "duration": 14400}}]},
                ),
            ]
        )
        with patch(
            "odoo.addons.tms_routing_ors.models.tms_route.requests.request",
            _request,
        ):
            measures = self.route._compute_route_path_ors()
        self.assertEqual(calls[0]["url"], ORS_GEOCODE_URL)
        self.assertEqual(calls[0]["headers"]["Authorization"], "test-key")
        self.assertEqual(calls[0]["timeout"], 30)
        self.assertEqual(calls[1]["url"], ORS_DIRECTIONS_URL)
        self.assertEqual(
            calls[1]["kwargs"]["json"]["coordinates"],
            [[-95.36, 29.76], [-96.79, 32.77]],
        )
        self.assertNotIn("options", calls[1]["kwargs"]["json"])
        self.assertAlmostEqual(measures["distance"], 360.0)
        self.assertAlmostEqual(measures["duration"], 4.0)

    def test_avoid_tolls_is_sent(self):
        self.destination.partner_latitude = 32.77
        self.destination.partner_longitude = -96.79
        self.route.avoid_tolls = True
        calls, _request = self._requests(
            [
                (
                    200,
                    {"routes": [{"summary": {"distance": 1000, "duration": 60}}]},
                )
            ]
        )
        with patch(
            "odoo.addons.tms_routing_ors.models.tms_route.requests.request",
            _request,
        ):
            self.route._compute_route_path_ors()
        self.assertEqual(
            calls[0]["kwargs"]["json"]["options"],
            {"avoid_features": ["tollways"]},
        )

    def test_missing_api_key(self):
        self.env["ir.config_parameter"].sudo().set_param("tms_routing_ors.api_key", "")
        with self.assertRaises(UserError):
            self.route._compute_route_path_ors()

    def test_http_error(self):
        calls, _request = self._requests([(401, {"error": "denied"})])
        with patch(
            "odoo.addons.tms_routing_ors.models.tms_route.requests.request",
            _request,
        ):
            with self.assertRaises(UserError):
                self.route._ors_request("GET", ORS_GEOCODE_URL)
        self.assertTrue(calls)

    def test_geocode_without_a_match(self):
        calls, _request = self._requests([(200, {"features": []})])
        with patch(
            "odoo.addons.tms_routing_ors.models.tms_route.requests.request",
            _request,
        ):
            with self.assertRaises(UserError):
                self.route._ors_geocode(self.destination)
        self.assertTrue(calls)

    def test_geocode_without_an_address(self):
        partner = self.env["res.partner"].create({"name": " "})
        with self.assertRaises(UserError):
            self.route._ors_geocode(partner)

    def test_path_needs_two_points(self):
        with patch.object(type(self.route), "_routing_points", return_value=[]):
            with self.assertRaises(UserError):
                self.route._compute_route_path_ors()

    def test_empty_path(self):
        self.destination.partner_latitude = 32.77
        self.destination.partner_longitude = -96.79
        _calls, _request = self._requests([(200, {"routes": []})])
        with patch(
            "odoo.addons.tms_routing_ors.models.tms_route.requests.request",
            _request,
        ):
            with self.assertRaises(UserError):
                self.route._compute_route_path_ors()

    def test_provider_is_offered(self):
        selection = (
            self.env["tms.route"]
            ._fields["routing_provider"]
            ._description_selection(self.env)
        )
        self.assertIn(("ors", "OpenRouteService"), selection)

    def test_settings_store_the_api_key(self):
        settings = self.env["res.config.settings"].create(
            {"tms_routing_ors_api_key": "stored-key"}
        )
        settings.execute()
        self.assertEqual(self.route._ors_api_key(), "stored-key")
        arch = self.env.ref("tms_routing_ors.res_config_settings_view_form").arch
        self.assertIn("tms_routing_ors_api_key", arch)
