# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError


class TmsRoute(models.Model):
    _inherit = "tms.route"

    stop_ids = fields.One2many("tms.route.stop", "route_id")
    avoid_tolls = fields.Boolean(
        help="Ask the provider for a path that does not use toll roads.",
    )
    routing_provider = fields.Selection(
        selection=lambda model: model._selection_routing_provider(),
    )
    routing_state = fields.Selection(
        selection=[
            ("draft", "Not requested"),
            ("pending", "Queued"),
            ("done", "Routed"),
            ("error", "Error"),
        ],
        default="draft",
        readonly=True,
        copy=False,
    )
    routing_error = fields.Text(readonly=True, copy=False)

    @api.model
    def _selection_routing_provider(self):
        return []

    def _routing_points(self):
        """Origin, ordered stops, then destination.

        A stop uses its own coordinates when either value is set. Otherwise
        the location contact is used.
        """
        self.ensure_one()
        points = [self._point_from_partner(self.origin_location_id)]
        for stop in self.stop_ids.sorted("sequence"):
            if stop.latitude or stop.longitude:
                points.append(
                    {
                        "partner": stop.location_id,
                        "latitude": stop.latitude,
                        "longitude": stop.longitude,
                    }
                )
            else:
                points.append(self._point_from_partner(stop.location_id))
        points.append(self._point_from_partner(self.destination_location_id))
        return points

    def _point_from_partner(self, partner):
        return {
            "partner": partner,
            "latitude": partner.partner_latitude,
            "longitude": partner.partner_longitude,
        }

    def _routing_measures(self, distance_meters, duration_seconds):
        """Convert provider meters and seconds into the route units."""
        self.ensure_one()
        meter = self.env.ref("uom.product_uom_meter")
        hour = self.env.ref("uom.product_uom_hour")
        distance_uom = self.distance_uom or self.env.ref("uom.product_uom_km")
        time_uom = self.estimated_time_uom or hour
        return {
            "distance": meter._compute_quantity(distance_meters, distance_uom),
            "distance_uom": distance_uom,
            "duration": hour._compute_quantity(duration_seconds / 3600.0, time_uom),
            "duration_uom": time_uom,
        }

    def _compute_route_path(self):
        self.ensure_one()
        if not self.routing_provider:
            raise UserError(self.env._("Choose a routing provider."))
        handler = getattr(self, f"_compute_route_path_{self.routing_provider}", None)
        if not handler:
            raise UserError(
                self.env._(
                    "The routing provider %(provider)s is not installed.",
                    provider=self.routing_provider,
                )
            )
        return handler()

    def _job_compute_route(self):
        for route in self:
            try:
                measures = route._compute_route_path()
            except UserError as error:
                route.write(
                    {
                        "routing_state": "error",
                        "routing_error": str(error),
                    }
                )
                continue
            route.write(
                {
                    "distance": measures["distance"],
                    "distance_uom": measures["distance_uom"].id,
                    "estimated_time": measures["duration"],
                    "estimated_time_uom": measures["duration_uom"].id,
                    "routing_state": "done",
                    "routing_error": False,
                }
            )

    def action_compute_route(self):
        for route in self:
            if not route.routing_provider:
                raise UserError(route.env._("Choose a routing provider."))
            route.write({"routing_state": "pending", "routing_error": False})
            route.with_delay(
                channel="root.routing",
                identity_key=f"tms.route.{route.id}",
                description=route.env._(
                    "Compute route %(name)s",
                    name=route.display_name,
                ),
            )._job_compute_route()
        return True
