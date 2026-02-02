# Copyright (C) 2025 KMEE (https://kmee.com.br)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class TMSOrder(models.Model):
    """Extend TMS Order with Leaflet map visualization for delivery stops."""

    _inherit = "tms.order"

    # Computed fields for map center (uses origin or first stop)
    map_center_latitude = fields.Float(
        compute="_compute_map_center",
        store=True,
    )
    map_center_longitude = fields.Float(
        compute="_compute_map_center",
        store=True,
    )

    @api.depends(
        "origin_id",
        "origin_id.partner_latitude",
        "origin_id.partner_longitude",
        "stop_ids",
        "stop_ids.latitude",
        "stop_ids.longitude",
    )
    def _compute_map_center(self):
        """Compute map center from origin or first stop."""
        for order in self:
            lat, lng = 0.0, 0.0

            # Try origin first
            if order.origin_id:
                lat = order.origin_id.partner_latitude or 0.0
                lng = order.origin_id.partner_longitude or 0.0

            # Fallback to first stop if origin has no coordinates
            if not lat and not lng and order.stop_ids:
                first_stop = order.stop_ids.sorted("sequence")[:1]
                if first_stop:
                    lat = first_stop.latitude or 0.0
                    lng = first_stop.longitude or 0.0

            order.map_center_latitude = lat
            order.map_center_longitude = lng

    def action_open_stops_map(self):
        """Open delivery stops in a Leaflet map view."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": f"Delivery Stops: {self.name}",
            "res_model": "tms.order.stop",
            "view_mode": "leaflet_map,list,form",
            "domain": [("order_id", "=", self.id)],
            "context": {
                "default_order_id": self.id,
                "search_default_order_id": self.id,
            },
        }

    def action_open_all_stops_map(self):
        """Open all delivery stops from selected orders in a map view."""
        return {
            "type": "ir.actions.act_window",
            "name": "All Delivery Stops",
            "res_model": "tms.order.stop",
            "view_mode": "leaflet_map,list,form",
            "domain": [("order_id", "in", self.ids)],
            "context": {
                "group_by_order": True,
            },
        }
