from odoo import api, fields, models


class TMSOrder(models.Model):
    _name = "tms.order"
    _inherit = ["tms.order", "capacity.utilization.mixin"]

    stop_ids = fields.One2many(
        "tms.order.stop",
        "order_id",
        string="Delivery Stops",
        help="Multiple delivery stops for this order",
        copy=True,
    )
    delivery_stop_ids = fields.One2many(
        "tms.order.stop",
        "order_id",
        string="Delivery Stops Only",
        domain=[("stop_type", "=", "delivery")],
        help="Only delivery stops (excludes origin/destination)",
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

    # Override mixin fields to add store=True and proper depends
    weight_utilization = fields.Float(
        compute="_compute_utilization",
        store=True,
    )
    volume_utilization = fields.Float(
        compute="_compute_utilization",
        store=True,
    )

    @api.depends(
        "vehicle_id",
        "vehicle_id.weight_capacity",
        "vehicle_id.volume_capacity",
    )
    def _compute_capacity_from_vehicle(self):
        return super()._compute_capacity_from_vehicle()

    @api.depends(
        "vehicle_id",
        "vehicle_id.weight_capacity",
        "vehicle_id.volume_capacity",
        "total_weight",
        "total_volume",
    )
    def _compute_utilization(self):
        return super()._compute_utilization()

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

    @api.depends(
        "stop_ids",
        "stop_ids.weight",
        "stop_ids.volume",
        "stop_ids.stop_type",
    )
    def _compute_totals(self):
        for order in self:
            # Only count delivery stops for totals (exclude origin/destination)
            delivery_stops = order.stop_ids.filtered(
                lambda s: s.stop_type == "delivery"
            )
            order.total_weight = sum(delivery_stops.mapped("weight"))
            order.total_volume = sum(delivery_stops.mapped("volume"))
            order.total_stops = len(delivery_stops)

    @api.depends("stop_ids", "stop_ids.unloading_time", "stop_ids.stop_type")
    def _compute_estimated_time(self):
        for order in self:
            # Only count delivery stops for unloading time
            delivery_stops = order.stop_ids.filtered(
                lambda s: s.stop_type == "delivery"
            )
            total_unloading_time = sum(delivery_stops.mapped("unloading_time"))
            # Convert minutes to hours
            order.estimated_total_time = total_unloading_time / 60.0

    @api.depends(
        "stop_ids",
        "stop_ids.latitude",
        "stop_ids.longitude",
        "stop_ids.stop_type",
        "stop_ids.sequence",
    )
    def _compute_google_maps_url(self):
        for order in self:
            # Use new method that relies on stop_type
            order.google_maps_url = order._generate_google_maps_url_from_stops()

    def _generate_google_maps_url_from_stops(self):
        """
        Generate Google Maps URL using stop_type to determine origin/destination.

        Returns:
            Google Maps URL string or None if insufficient coordinates
        """
        self.ensure_one()

        # Get stops by type
        origin_stop = self.stop_ids.filtered(lambda s: s.stop_type == "origin")[:1]
        destination_stop = self.stop_ids.filtered(
            lambda s: s.stop_type == "destination"
        )[:1]
        delivery_stops = self.stop_ids.filtered(
            lambda s: s.stop_type == "delivery"
        ).sorted("sequence")

        # Collect all coordinates in order
        all_coords = []

        # Origin
        if origin_stop and origin_stop.latitude and origin_stop.longitude:
            all_coords.append((origin_stop.latitude, origin_stop.longitude))

        # Delivery stops
        for stop in delivery_stops:
            if stop.latitude and stop.longitude:
                all_coords.append((stop.latitude, stop.longitude))

        # Destination
        if (
            destination_stop
            and destination_stop.latitude
            and destination_stop.longitude
        ):
            all_coords.append((destination_stop.latitude, destination_stop.longitude))

        if len(all_coords) < 2:
            return None

        # First is origin, last is destination
        origin = f"{all_coords[0][0]},{all_coords[0][1]}"
        destination = f"{all_coords[-1][0]},{all_coords[-1][1]}"

        # Middle coords are waypoints
        waypoints = []
        for lat, lon in all_coords[1:-1]:
            waypoints.append(f"{lat},{lon}")

        waypoints_str = "|".join(waypoints) if waypoints else ""

        url = (
            f"https://www.google.com/maps/dir/?api=1"
            f"&origin={origin}&destination={destination}"
        )
        if waypoints_str:
            url += f"&waypoints={waypoints_str}"

        return url

    @staticmethod
    def generate_google_maps_url(
        stop_coordinates, origin_coords=None, destination_coords=None
    ):
        """
        Generate Google Maps URL for a route with waypoints.
        Kept for backward compatibility.

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

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to auto-create endpoint stops."""
        orders = super().create(vals_list)
        orders._create_endpoint_stops()
        return orders

    def write(self, vals):
        """Override write to sync stop states."""
        res = super().write(vals)
        if "stage_id" in vals:
            self._sync_stop_states()
        return res

    def _create_endpoint_stops(self):
        """
        Create origin and destination stops based on origin_id/destination_id fields.
        Called automatically on order creation.
        """
        Stop = self.env["tms.order.stop"]
        for order in self:
            existing_types = set(order.stop_ids.mapped("stop_type"))

            # Create origin stop if not exists and origin_id is set
            if "origin" not in existing_types and order.origin_id:
                Stop.create(
                    {
                        "order_id": order.id,
                        "stop_type": "origin",
                        "location_id": order.origin_id.id,
                        "sequence": 0,
                        "company_id": order.company_id.id,
                    }
                )

            # Create destination stop if not exists and destination_id is set
            # Note: We create even if same as origin - map will handle deduplication
            if "destination" not in existing_types and order.destination_id:
                Stop.create(
                    {
                        "order_id": order.id,
                        "stop_type": "destination",
                        "location_id": order.destination_id.id,
                        "sequence": 9999,
                        "company_id": order.company_id.id,
                    }
                )

    def _sync_stop_states(self):
        """Sync stop states based on order stage configuration"""
        for order in self:
            if not order.stage_id or not order.stage_id.stop_state_sync:
                continue
            stop_state = order.stage_id.stop_state_sync
            order.stop_ids.write({"state": stop_state})
