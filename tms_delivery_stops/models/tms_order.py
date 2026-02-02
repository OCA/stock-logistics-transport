from odoo import api, fields, models


class TMSOrder(models.Model):
    _inherit = "tms.order"

    stop_ids = fields.One2many(
        "tms.order.stop",
        "order_id",
        string="Delivery Stops",
        help="Multiple delivery stops for this order",
        copy=True,
    )
    total_weight = fields.Float(
        compute="_compute_totals",
        store=True,
    )
    total_volume = fields.Float(
        compute="_compute_totals",
        store=True,
    )
    total_stops = fields.Integer(
        compute="_compute_totals",
        store=True,
    )
    estimated_total_time = fields.Float(
        string="Estimated Total Time (hours)",
        compute="_compute_estimated_time",
        store=False,
    )
    google_maps_url = fields.Char(
        string="Google Maps Route",
        compute="_compute_google_maps_url",
        store=True,
        help="Google Maps URL with route for all delivery stops",
    )

    @api.model
    def default_get(self, fields_list):
        """Set default origin and destination from company config"""
        res = super().default_get(fields_list)
        company = self.env.company
        if "origin_id" in fields_list and not res.get("origin_id"):
            if company.tms_default_origin_location_id:
                res["origin_id"] = company.tms_default_origin_location_id.id
        if "destination_id" in fields_list and not res.get("destination_id"):
            if company.tms_default_destination_location_id:
                res["destination_id"] = company.tms_default_destination_location_id.id
        return res

    @api.depends("stop_ids", "stop_ids.weight", "stop_ids.volume")
    def _compute_totals(self):
        for order in self:
            order.total_weight = sum(order.stop_ids.mapped("weight"))
            order.total_volume = sum(order.stop_ids.mapped("volume"))
            order.total_stops = len(order.stop_ids)

    @api.depends("stop_ids", "stop_ids.unloading_time")
    def _compute_estimated_time(self):
        for order in self:
            total_unloading_time = sum(order.stop_ids.mapped("unloading_time"))
            # Convert minutes to hours
            order.estimated_total_time = total_unloading_time / 60.0

    @api.depends(
        "stop_ids",
        "stop_ids.latitude",
        "stop_ids.longitude",
        "origin_id",
        "origin_id.partner_latitude",
        "origin_id.partner_longitude",
        "destination_id",
        "destination_id.partner_latitude",
        "destination_id.partner_longitude",
    )
    def _compute_google_maps_url(self):
        for order in self:
            # Get origin coordinates from order.origin_id if available
            origin_coords = None
            if (
                order.origin_id
                and order.origin_id.partner_latitude
                and order.origin_id.partner_longitude
            ):
                origin_coords = (
                    order.origin_id.partner_latitude,
                    order.origin_id.partner_longitude,
                )

            # Get destination coordinates from order.destination_id if available
            destination_coords = None
            if (
                order.destination_id
                and order.destination_id.partner_latitude
                and order.destination_id.partner_longitude
            ):
                destination_coords = (
                    order.destination_id.partner_latitude,
                    order.destination_id.partner_longitude,
                )

            # Collect stop coordinates
            stop_coordinates = []
            for stop in order.stop_ids.sorted("sequence"):
                if stop.latitude and stop.longitude:
                    stop_coordinates.append((stop.latitude, stop.longitude))

            order.google_maps_url = self.generate_google_maps_url(
                stop_coordinates, origin_coords, destination_coords
            )

    @staticmethod
    def generate_google_maps_url(
        stop_coordinates, origin_coords=None, destination_coords=None
    ):
        """
        Generate Google Maps URL for a route with waypoints.

        Args:
            stop_coordinates: List of (latitude, longitude) tuples for stops
            origin_coords: Optional tuple (lat, lon) for origin location
            destination_coords: Optional tuple (lat, lon) for destination location

        Returns:
            Google Maps URL string or None if insufficient coordinates
        """
        # Determine origin
        if origin_coords:
            origin = f"{origin_coords[0]},{origin_coords[1]}"
        elif stop_coordinates:
            origin = f"{stop_coordinates[0][0]},{stop_coordinates[0][1]}"
        else:
            return None

        # Determine destination
        if destination_coords:
            destination = f"{destination_coords[0]},{destination_coords[1]}"
        elif stop_coordinates:
            destination = f"{stop_coordinates[-1][0]},{stop_coordinates[-1][1]}"
        else:
            return None

        # Build waypoints (all stops if origin/destination are from order,
        # otherwise stops between first and last)
        waypoints = []
        if origin_coords or destination_coords:
            # Origin or destination is from order, all stops are waypoints
            for lat, lon in stop_coordinates:
                waypoints.append(f"{lat},{lon}")
        else:
            # Fallback: use stops between first and last as waypoints
            for lat, lon in stop_coordinates[1:-1]:
                waypoints.append(f"{lat},{lon}")

        waypoints_str = "|".join(waypoints) if waypoints else ""

        url = (
            f"https://www.google.com/maps/dir/?api=1"
            f"&origin={origin}&destination={destination}"
        )
        if waypoints_str:
            url += f"&waypoints={waypoints_str}"

        return url

    @api.onchange("tms_team_id")
    def _onchange_tms_team_id(self):
        """Fill origin and destination from team defaults"""
        if self.tms_team_id and not self.route:
            if self.tms_team_id.default_origin_location_id:
                self.origin_id = self.tms_team_id.default_origin_location_id
            if self.tms_team_id.default_destination_location_id:
                self.destination_id = self.tms_team_id.default_destination_location_id

    def write(self, vals):
        """Override write to sync stop states when stage_id changes"""
        res = super().write(vals)
        if "stage_id" in vals:
            self._sync_stop_states()
        return res

    def _sync_stop_states(self):
        """Sync stop states based on order stage configuration"""
        for order in self:
            if not order.stage_id or not order.stage_id.stop_state_sync:
                continue
            stop_state = order.stage_id.stop_state_sync
            order.stop_ids.write({"state": stop_state})
