# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import http
from odoo.exceptions import AccessError, UserError
from odoo.http import request

from odoo.addons.portal.controllers.portal import CustomerPortal


class PickupPortal(CustomerPortal):
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if "pickup_count" in counters:
            values["pickup_count"] = request.env["tms.order"].search_count([])
        return values

    def _portal_float(self, value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @http.route(["/my/pickups"], type="http", auth="user", website=True)
    def portal_my_pickups(self, **kwargs):
        values = self._prepare_portal_layout_values()
        trips = request.env["tms.order"].search([])
        values.update(
            {
                "page_name": "pickup",
                "trip": False,
                "trips": trips.sudo(),
            }
        )
        return request.render("tms_portal.portal_my_pickups", values)

    @http.route(
        ["/my/pickups/<int:trip_id>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_pickup(self, trip_id, **kwargs):
        trip = request.env["tms.order"].browse(trip_id)
        try:
            trip.check_access("read")
        except AccessError:
            return request.redirect("/my")
        values = self._prepare_portal_layout_values()
        values.update(
            {
                "page_name": "pickup",
                "trip": trip.sudo(),
            }
        )
        return request.render("tms_portal.portal_my_pickup", values)

    @http.route(
        ["/my/pickups/<int:trip_id>/add"],
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
    )
    def portal_add_pickup(self, trip_id, **post):
        try:
            trip = request.env["tms.order"].browse(trip_id)
            parent = request.env["tms.cargo"].browse(int(post.get("parent_id") or 0))
            trip.add_pickup(
                parent,
                {
                    "name": post.get("name"),
                    "quantity": self._portal_float(post.get("quantity")),
                    "weight": self._portal_float(post.get("weight")),
                    "volume": self._portal_float(post.get("volume")),
                },
            )
        except (AccessError, UserError, ValueError):
            return request.redirect("/my")
        return request.redirect(f"/my/pickups/{trip_id}")
