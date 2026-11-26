# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json

from odoo import api, fields, models
from odoo.exceptions import UserError

from odoo.addons.tms_map.demo.location_perimeters import PERIMETERS


class ResPartner(models.Model):
    _inherit = "res.partner"

    tms_map_shape = fields.Selection(
        [
            ("point", "Point"),
            ("area", "Area"),
        ],
        string="On the map",
        help="Point shows the coordinates. Area shows the perimeter drawn "
        "on the map. Leave it empty to keep this contact off the map.",
    )
    tms_geofence = fields.Json(
        string="Geofence",
        help="Corners of the perimeter, each one a latitude and longitude.",
    )

    @api.model
    def _demo_apply_location_perimeters(self):
        """Store the demo perimeters. Leave a location that already has one."""
        for xmlid, corners in PERIMETERS.items():
            partner = self.env.ref(xmlid, raise_if_not_found=False)
            if not partner or partner.tms_geofence:
                continue
            partner.tms_map_set_geofence(corners)

    @api.model
    def tms_map_locations(self):
        """Points and perimeters of partners marked as transport locations."""
        rows = []
        partners = self.search([("tms_location", "=", True)])
        for partner in partners:
            if partner.tms_map_shape == "area":
                corners = partner._tms_map_corners(partner.tms_geofence)
                if len(corners) < 3:
                    continue
                rows.append(
                    {
                        "id": partner.id,
                        "name": partner.display_name,
                        "shape": "area",
                        "perimeter": corners,
                    }
                )
                continue
            if partner.tms_map_shape != "point":
                continue
            if not (partner.partner_latitude or partner.partner_longitude):
                continue
            rows.append(
                {
                    "id": partner.id,
                    "name": partner.display_name,
                    "shape": "point",
                    "latitude": partner.partner_latitude,
                    "longitude": partner.partner_longitude,
                }
            )
        return rows

    def tms_map_set_coordinates(self, latitude, longitude):
        """Store a pin dropped on the partner map."""
        self.ensure_one()
        self.write(
            {
                "partner_latitude": latitude,
                "partner_longitude": longitude,
            }
        )
        return True

    def tms_map_set_geofence(self, perimeter):
        """Store the perimeter drawn on the map, or clear it."""
        self.ensure_one()
        corners = self._tms_map_corners(perimeter)
        if not corners:
            self.tms_geofence = False
            return True
        if len(corners) < 3:
            raise UserError(self.env._("A perimeter needs at least three corners."))
        latitude = sum(corner[0] for corner in corners) / len(corners)
        longitude = sum(corner[1] for corner in corners) / len(corners)
        self.write(
            {
                "tms_map_shape": "area",
                "tms_geofence": corners,
                "partner_latitude": latitude,
                "partner_longitude": longitude,
            }
        )
        return True

    def _tms_map_corners(self, perimeter):
        if isinstance(perimeter, str):
            perimeter = json.loads(perimeter or "[]")
        corners = []
        for pair in perimeter or []:
            if not isinstance(pair, (list, tuple)) or len(pair) < 2:
                continue
            corners.append([round(float(pair[0]), 7), round(float(pair[1]), 7)])
        return corners
