# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
from unittest.mock import patch

import requests

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase

from odoo.addons.tms_telematics_geotab.models.geotab_api import (
    FEED_LIMIT,
    GeotabAPI,
    GeotabError,
)


def _response(body):
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return body

    return Response()


class TestGeotab(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        brand = cls.env["fleet.vehicle.model.brand"].create({"name": "Geotab"})
        model = cls.env["fleet.vehicle.model"].create(
            {"name": "GO", "brand_id": brand.id}
        )
        cls.vehicle = cls.env["fleet.vehicle"].create(
            {
                "model_id": model.id,
                "license_plate": "GEO-001",
                "vin_sn": "VIN-GEO-001",
                "odometer_unit": "kilometers",
            }
        )
        cls.account = cls.env["tms.telematics.account"].create(
            {
                "name": "Geotab",
                "provider": "geotab",
                "server_url": "https://my.geotab.com/apiv1",
                "database_name": "demo",
                "login": "user@example.com",
                "password": "secret",
            }
        )

    def test_provider_selection_and_default_server(self):
        selection = self.env["tms.telematics.account"]._fields[
            "provider"
        ]._description_selection(self.env)
        labels = dict(selection)
        self.assertEqual(labels["geotab"], "Geotab")
        account = self.env["tms.telematics.account"].new({"provider": "geotab"})
        account._onchange_provider_geotab()
        self.assertEqual(account.server_url, "https://my.geotab.com/apiv1")
        kept = self.env["tms.telematics.account"].new(
            {"provider": "geotab", "server_url": "https://att.example/apiv1"}
        )
        kept._onchange_provider_geotab()
        self.assertEqual(kept.server_url, "https://att.example/apiv1")

    def test_mapping(self):
        api = GeotabAPI(self.account)
        self.assertFalse(api.map_rows("Unknown", [{"id": "x"}]))
        self.assertFalse(api._map_LogRecord({"id": "x"}))
        position = api._map_LogRecord(
            {
                "id": "log1",
                "device": "d1",
                "dateTime": "2026-09-10T15:00:00.000Z",
                "latitude": 25.6,
                "longitude": -100.3,
                "speed": -1,
            }
        )[0]
        self.assertEqual(position["device_external_id"], "d1")
        self.assertIsNone(position["speed"])
        start_only = api._map_Trip(
            {"device": {"id": "d1"}, "start": "2026-09-10T08:00:00Z"}
        )
        self.assertEqual(len(start_only), 1)
        self.assertFalse(api._map_Trip({"device": {"id": "d1"}}))
        trip = api._map_Trip(
            {
                "device": {"id": "d1"},
                "start": "2026-09-10T08:00:00.000Z",
                "stop": "2026-09-10T10:00:00.000Z",
                "odometer": 150000,
                "distance": 10,
                "stopPoint": {"x": -100.3, "y": 25.6},
            }
        )
        self.assertEqual(trip[0]["odometer_km"], 140)
        self.assertEqual(trip[1]["odometer_km"], 150)
        self.assertEqual(trip[1]["latitude"], 25.6)
        derived = api._map_FillUp(
            {
                "id": "f1",
                "device": {"id": "d1"},
                "volume": 0,
                "derivedVolume": 40,
                "odometer": 150000,
                "dateTime": "2026-09-10T11:00:00Z",
            }
        )[0]
        self.assertEqual(derived["fuel_liters"], 40)
        self.assertEqual(derived["odometer_km"], 150)
        empty = api._map_FillUp(
            {"id": "f2", "device": {"id": "d1"}, "volume": 0, "derivedVolume": -1}
        )[0]
        self.assertIsNone(empty["fuel_liters"])
        self.assertFalse(api._map_FillUp({"id": "f3"}))
        devices = api.map_devices(
            [
                {},
                {
                    "id": "d1",
                    "name": "Truck",
                    "vehicleIdentificationNumber": "VIN-GEO-001",
                    "licensePlate": "GEO-001",
                },
            ]
        )
        self.assertEqual(devices[0]["vin"], "VIN-GEO-001")

    def _feeds(self):
        return {
            "Device": {
                "data": [
                    {
                        "id": "d1",
                        "name": "Truck",
                        "vehicleIdentificationNumber": "VIN-GEO-001",
                        "licensePlate": "GEO-001",
                    }
                ],
                "toVersion": "dev1",
            },
            "LogRecord": {
                "data": [
                    {
                        "id": "log1",
                        "device": {"id": "d1"},
                        "dateTime": "2026-09-10T15:00:00.000Z",
                        "latitude": 25.6,
                        "longitude": -100.3,
                        "speed": 70,
                    }
                ],
                "toVersion": "log1",
            },
            "Trip": {
                "data": [
                    {
                        "device": {"id": "d1"},
                        "start": "2026-09-10T08:00:00.000Z",
                        "stop": "2026-09-10T10:00:00.000Z",
                        "odometer": 150000,
                        "distance": 10,
                        "stopPoint": {"x": -100.3, "y": 25.6},
                    }
                ],
                "toVersion": "trip1",
            },
            "FillUp": {
                "data": [
                    {
                        "id": "fill1",
                        "device": {"id": "d1"},
                        "dateTime": "2026-09-10T11:00:00.000Z",
                        "volume": 40,
                        "odometer": 150000,
                        "location": {"x": -100.3, "y": 25.6},
                    }
                ],
                "toVersion": "fill1",
            },
        }

    def test_pull_imports_devices_trips_and_fills(self):
        trip = self.env["tms.order"].create(
            {"name": "GEO/1", "vehicle_id": self.vehicle.id}
        )
        feeds = self._feeds()

        def post(url, json, timeout):
            self.assertEqual(url, "https://my.geotab.com/apiv1")
            method = json["method"]
            if method == "Authenticate":
                return _response(
                    {
                        "result": {
                            "credentials": {
                                "sessionId": "session",
                                "userName": "user@example.com",
                                "database": "demo",
                            },
                            "path": "ThisServer",
                        }
                    }
                )
            return _response({"result": feeds[json["params"]["typeName"]]})

        with patch(
            "odoo.addons.tms_telematics_geotab.models.geotab_api.requests.post",
            post,
        ):
            self.account._pull()
        device = self.account.device_ids
        self.assertEqual(device.vehicle_id, self.vehicle)
        self.assertEqual(device.vin, "VIN-GEO-001")
        self.assertEqual(trip.odometer_start, 140)
        self.assertEqual(trip.odometer_end, 150)
        self.assertEqual(
            set(self.account.reading_ids.mapped("event")),
            {"position", "trip_start", "trip_end", "fill"},
        )
        cursor = json.loads(self.account.feed_cursor)
        self.assertEqual(cursor["LogRecord"], "log1")
        self.assertEqual(self.account.session_server, "https://my.geotab.com/apiv1")
        self.assertTrue(self.account.last_sync)

    def test_authenticate_follows_the_federation_host(self):
        def post(url, json, timeout):
            self.assertEqual(json["method"], "Authenticate")
            return _response(
                {
                    "result": {
                        "credentials": {"sessionId": "abc"},
                        "path": "att.example",
                    }
                }
            )

        with patch(
            "odoo.addons.tms_telematics_geotab.models.geotab_api.requests.post",
            post,
        ):
            GeotabAPI(self.account).authenticate()
        self.assertEqual(self.account.session_id, "abc")
        self.assertEqual(self.account.session_server, "https://att.example/apiv1")

    def test_a_live_session_is_reused(self):
        self.account.write(
            {
                "session_id": "live",
                "session_expires": fields.Datetime.add(fields.Datetime.now(), days=1),
            }
        )

        def post(url, json, timeout):
            raise AssertionError("Authenticate was called")

        with patch(
            "odoo.addons.tms_telematics_geotab.models.geotab_api.requests.post",
            post,
        ):
            GeotabAPI(self.account).authenticate()
        self.assertEqual(self.account.session_id, "live")

    def test_an_expired_session_is_refreshed_once(self):
        self.account.write(
            {
                "session_id": "old",
                "session_expires": fields.Datetime.add(fields.Datetime.now(), days=1),
            }
        )
        calls = []

        def post(url, json, timeout):
            calls.append(json["method"])
            if json["method"] == "GetFeed" and calls.count("GetFeed") == 1:
                return _response(
                    {
                        "error": {
                            "message": "expired",
                            "data": {"type": "InvalidUserException"},
                        }
                    }
                )
            if json["method"] == "Authenticate":
                return _response(
                    {
                        "result": {
                            "credentials": {"sessionId": "new"},
                            "path": "ThisServer",
                        }
                    }
                )
            return _response({"result": {"data": [{"id": "1"}], "toVersion": "v2"}})

        with patch(
            "odoo.addons.tms_telematics_geotab.models.geotab_api.requests.post",
            post,
        ):
            result = GeotabAPI(self.account).call("GetFeed", {"typeName": "LogRecord"})
        self.assertEqual(self.account.session_id, "new")
        self.assertEqual(result["toVersion"], "v2")
        self.assertEqual(calls.count("Authenticate"), 1)

    def test_a_session_error_is_not_retried_twice(self):
        self.account.session_id = "old"

        def post(url, json, timeout):
            if json["method"] == "Authenticate":
                return _response(
                    {
                        "result": {
                            "credentials": {"sessionId": "new"},
                            "path": "ThisServer",
                        }
                    }
                )
            return _response(
                {
                    "error": {
                        "message": "expired",
                        "data": {"type": "SessionExpiredException"},
                    }
                }
            )

        with patch(
            "odoo.addons.tms_telematics_geotab.models.geotab_api.requests.post",
            post,
        ):
            with self.assertRaises(GeotabError):
                GeotabAPI(self.account).call("GetFeed", {"typeName": "LogRecord"})

    def test_api_errors_and_transport_errors(self):
        self.account.session_id = "live"
        api = GeotabAPI(self.account)

        def over_limit(url, json, timeout):
            return _response(
                {
                    "error": {
                        "message": "slow down",
                        "data": {"type": "OverLimitException"},
                    }
                }
            )

        with patch(
            "odoo.addons.tms_telematics_geotab.models.geotab_api.requests.post",
            over_limit,
        ):
            with self.assertRaises(GeotabError):
                api.call("GetFeed", {"typeName": "LogRecord"})

        def http_error(url, json, timeout):
            class Response:
                def raise_for_status(self):
                    raise requests.HTTPError("down")

                def json(self):
                    return {}

            return Response()

        with patch(
            "odoo.addons.tms_telematics_geotab.models.geotab_api.requests.post",
            http_error,
        ):
            with self.assertRaises(UserError):
                api.call("GetFeed", {"typeName": "LogRecord"})

        def bad_json(url, json, timeout):
            class Response:
                def raise_for_status(self):
                    return None

                def json(self):
                    raise ValueError("nope")

            return Response()

        with patch(
            "odoo.addons.tms_telematics_geotab.models.geotab_api.requests.post",
            bad_json,
        ):
            with self.assertRaises(UserError):
                api.call("GetFeed", {"typeName": "LogRecord"})

        def not_object(url, json, timeout):
            return _response([])

        with patch(
            "odoo.addons.tms_telematics_geotab.models.geotab_api.requests.post",
            not_object,
        ):
            with self.assertRaises(UserError):
                api.call("GetFeed", {"typeName": "LogRecord"})

    def test_missing_credentials_block_the_pull(self):
        self.account.password = False
        with self.assertRaises(UserError):
            GeotabAPI(self.account).authenticate()

    def test_pull_geotab_reports_an_api_error(self):
        with patch(
            "odoo.addons.tms_telematics_geotab.models.tms_telematics_account.GeotabAPI"
        ) as api:
            api.return_value.pull.side_effect = GeotabError("nope")
            with self.assertRaises(UserError):
                self.account._pull_geotab()

    def test_feed_pages_and_a_bad_cursor(self):
        pages = {"n": 0}

        def call(method, params, authenticated=True, retry=True):
            pages["n"] += 1
            return {"data": [{"id": str(pages["n"])}], "toVersion": str(pages["n"])}

        api = GeotabAPI(self.account)
        module = "odoo.addons.tms_telematics_geotab.models.geotab_api"
        with patch.object(api, "call", call), patch(module + ".FEED_LIMIT", 1), patch(
            module + ".MAX_FEED_PAGES", 2
        ):
            rows, version = api.get_feed("LogRecord", None)
        self.assertEqual(len(rows), 2)
        self.assertEqual(version, "2")
        self.assertEqual(pages["n"], 2)

        def short(method, params, authenticated=True, retry=True):
            self.assertNotIn("fromVersion", params)
            return {"data": [{"id": "only"}], "toVersion": "once"}

        with patch.object(api, "call", short):
            rows, version = api.get_feed("LogRecord", None)
        self.assertEqual(rows[0]["id"], "only")
        self.assertLess(len(rows), FEED_LIMIT)

        def weird(method, params, authenticated=True, retry=True):
            return "x"

        with patch.object(api, "call", weird):
            rows, version = api.get_feed("LogRecord", "cursor")
        self.assertFalse(rows)
        self.assertEqual(version, "cursor")

        self.account.feed_cursor = "["
        with patch.object(api, "authenticate"), patch.object(
            api, "get_feed", return_value=([], "v")
        ):
            readings, cursor = api.pull()
        self.assertFalse(readings)
        self.assertEqual(json.loads(cursor)["Device"], "v")

        self.account.feed_cursor = "[]"
        with patch.object(api, "authenticate"), patch.object(
            api, "get_feed", return_value=([], "w")
        ):
            readings, cursor = api.pull()
        self.assertEqual(json.loads(cursor)["FillUp"], "w")

    def test_endpoint_defaults_when_the_server_is_empty(self):
        self.account.server_url = False
        self.assertEqual(
            GeotabAPI(self.account).endpoint(), "https://my.geotab.com/apiv1"
        )
