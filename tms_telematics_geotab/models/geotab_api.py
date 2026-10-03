# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json

import requests

from odoo import fields
from odoo.exceptions import UserError

SESSION_ERROR_TYPES = {"InvalidUserException", "SessionExpiredException"}
FEED_TYPES = ("LogRecord", "Trip", "FillUp")
FEED_LIMIT = 1000
MAX_FEED_PAGES = 5
DEFAULT_SERVER = "https://my.geotab.com/apiv1"


class GeotabError(Exception):
    def __init__(self, message, error_type=None):
        super().__init__(message)
        self.error_type = error_type


def _device_id(row):
    device = row.get("device")
    if isinstance(device, dict):
        return device.get("id")
    return device


def _meters_to_km(value):
    if not value:
        return None
    return float(value) / 1000.0


def _point(point):
    if not isinstance(point, dict):
        return None, None
    return point.get("y"), point.get("x")


class GeotabAPI:
    """JSON-RPC client for MyGeotab and the AT&T Fleet Management host."""

    def __init__(self, account):
        self.account = account

    def endpoint(self):
        url = self.account.session_server or self.account.server_url or DEFAULT_SERVER
        return url.rstrip("/")

    def _credentials(self):
        account = self.account
        return {
            "database": account.database_name,
            "sessionId": account.session_id,
            "userName": account.login,
        }

    def call(self, method, params, authenticated=True, retry=True):
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": dict(params),
            "id": 1,
        }
        if authenticated:
            if not self.account.session_id:
                self.authenticate()
            payload["params"]["credentials"] = self._credentials()
        try:
            response = requests.post(self.endpoint(), json=payload, timeout=60)
            response.raise_for_status()
            body = response.json()
        except requests.RequestException as error:
            raise UserError(self.account.env._("The Geotab request failed.")) from error
        except ValueError as error:
            raise UserError(
                self.account.env._("Geotab returned a response that is not JSON.")
            ) from error
        if not isinstance(body, dict):
            raise UserError(
                self.account.env._("Geotab returned a response that is not JSON.")
            )
        if body.get("error"):
            err = body["error"]
            data = err.get("data") or {}
            error_type = data.get("type")
            message = err.get("message") or self.account.env._(
                "The Geotab request failed."
            )
            if retry and authenticated and error_type in SESSION_ERROR_TYPES:
                self.account.session_id = False
                self.account.session_expires = False
                self.authenticate()
                return self.call(method, params, authenticated=True, retry=False)
            raise GeotabError(message, error_type)
        return body.get("result")

    def authenticate(self):
        account = self.account
        expires = account.session_expires
        if account.session_id and expires and expires > fields.Datetime.now():
            return
        if not account.database_name or not account.login or not account.password:
            raise UserError(
                account.env._("Set the database, login, and password before pulling.")
            )
        result = self.call(
            "Authenticate",
            {
                "database": account.database_name,
                "userName": account.login,
                "password": account.password,
            },
            authenticated=False,
        )
        result = result or {}
        credentials = result.get("credentials") or {}
        path = result.get("path") or "ThisServer"
        server = account.server_url or DEFAULT_SERVER
        if path != "ThisServer":
            server = f"https://{path}/apiv1"
        account.write(
            {
                "session_id": credentials.get("sessionId"),
                "session_server": server.rstrip("/"),
                "session_expires": fields.Datetime.add(fields.Datetime.now(), days=13),
            }
        )

    def get_feed(self, type_name, from_version):
        collected = []
        version = from_version
        for _page in range(MAX_FEED_PAGES):
            params = {"typeName": type_name, "resultsLimit": FEED_LIMIT}
            if version:
                params["fromVersion"] = version
            result = self.call("GetFeed", params) or {}
            if not isinstance(result, dict):
                break
            rows = result.get("data") or []
            version = result.get("toVersion") or version
            collected.extend(rows)
            if len(rows) < FEED_LIMIT:
                break
        return collected, version

    def pull(self):
        self.authenticate()
        try:
            cursor = json.loads(self.account.feed_cursor or "{}")
        except json.JSONDecodeError:
            cursor = {}
        if not isinstance(cursor, dict):
            cursor = {}
        devices, cursor["Device"] = self.get_feed("Device", cursor.get("Device"))
        self.account._sync_devices(self.map_devices(devices))
        readings = []
        for type_name in FEED_TYPES:
            rows, cursor[type_name] = self.get_feed(type_name, cursor.get(type_name))
            readings.extend(self.map_rows(type_name, rows))
        return readings, json.dumps(cursor, sort_keys=True)

    def map_devices(self, rows):
        mapped = []
        for row in rows or []:
            external_id = row.get("id")
            if not external_id:
                continue
            mapped.append(
                {
                    "external_id": external_id,
                    "name": row.get("name") or external_id,
                    "vin": row.get("vehicleIdentificationNumber") or False,
                    "license_plate": row.get("licensePlate") or False,
                }
            )
        return mapped

    def map_rows(self, type_name, rows):
        mapper = getattr(self, f"_map_{type_name}", None)
        if not mapper:
            return []
        readings = []
        for row in rows or []:
            readings.extend(mapper(row))
        return readings

    def _map_LogRecord(self, row):
        external_id = row.get("id")
        device_id = _device_id(row)
        if not external_id or not device_id:
            return []
        speed = row.get("speed")
        if speed is not None and speed < 0:
            speed = None
        return [
            {
                "external_id": external_id,
                "device_external_id": device_id,
                "event": "position",
                "timestamp": row.get("dateTime"),
                "latitude": row.get("latitude"),
                "longitude": row.get("longitude"),
                "speed": speed,
            }
        ]

    def _map_Trip(self, row):
        device_id = _device_id(row)
        if not device_id or not row.get("start"):
            return []
        end_km = _meters_to_km(row.get("odometer"))
        distance = row.get("distance") or 0.0
        start_km = None if end_km is None else end_km - distance
        readings = [
            {
                "external_id": f"trip-start:{device_id}:{row['start']}",
                "device_external_id": device_id,
                "event": "trip_start",
                "timestamp": row["start"],
                "odometer_km": start_km,
                "ignition": True,
            }
        ]
        stop = row.get("stop")
        if not stop:
            return readings
        latitude, longitude = _point(row.get("stopPoint"))
        readings.append(
            {
                "external_id": f"trip-end:{device_id}:{stop}",
                "device_external_id": device_id,
                "event": "trip_end",
                "timestamp": stop,
                "odometer_km": end_km,
                "ignition": False,
                "latitude": latitude,
                "longitude": longitude,
            }
        )
        return readings

    def _map_FillUp(self, row):
        external_id = row.get("id")
        device_id = _device_id(row)
        if not external_id or not device_id:
            return []
        volume = row.get("volume") or 0.0
        if volume <= 0:
            derived = row.get("derivedVolume") or 0.0
            volume = derived if derived > 0 else None
        latitude, longitude = _point(row.get("location"))
        cost = row.get("cost") or 0.0
        return [
            {
                "external_id": external_id,
                "device_external_id": device_id,
                "event": "fill",
                "timestamp": row.get("dateTime"),
                "odometer_km": _meters_to_km(row.get("odometer")),
                "fuel_liters": volume,
                "fuel_cost": cost if cost > 0 else False,
                "latitude": latitude,
                "longitude": longitude,
            }
        ]
