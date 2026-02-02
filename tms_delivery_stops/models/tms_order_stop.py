from odoo import _, api, fields, models
from odoo.exceptions import UserError


class TMSOrderStop(models.Model):
    _name = "tms.order.stop"
    _description = "TMS Order Delivery Stop"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "order_id, sequence"

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    order_id = fields.Many2one(
        "tms.order",
        string="Order",
        required=False,
        ondelete="set null",
        index=True,
    )
    sequence = fields.Integer(
        default=10,
        help="Order of the stop in the route",
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Delivery Partner",
        required=True,
        help="Recipient of the delivery",
    )
    weight = fields.Float(
        help="Weight of the delivery",
    )
    weight_uom_id = fields.Many2one(
        "uom.uom",
        string="Weight UoM",
        domain=[("category_id.name", "=", "Weight")],
        help="Unit of measure for weight",
        default=lambda self: self.env.ref(
            "uom.product_uom_kgm", raise_if_not_found=False
        ),
    )
    volume = fields.Float(
        help="Volume of the delivery",
    )
    volume_uom_id = fields.Many2one(
        "uom.uom",
        string="Volume UoM",
        domain=[("category_id.name", "=", "Volume")],
        help="Unit of measure for volume",
        default=lambda self: self.env.ref(
            "uom.product_uom_cubic_meter", raise_if_not_found=False
        ),
    )
    package_count = fields.Integer(
        help="Number of packages/boxes in this delivery",
    )
    unloading_time = fields.Float(
        string="Unloading Time (minutes)",
        default=lambda self: self.company_id.tms_default_unloading_time or 30.0,
        help="Minimum unloading time in minutes",
    )

    scheduled_date = fields.Datetime(
        help="Scheduled delivery date/time",
    )
    latitude = fields.Float(
        related="partner_id.partner_latitude",
        string="Latitude",
        readonly=True,
    )
    longitude = fields.Float(
        related="partner_id.partner_longitude",
        string="Longitude",
        readonly=True,
    )
    address_complete = fields.Char(
        string="Complete Address",
        compute="_compute_address_complete",
        store=False,
    )
    display_address = fields.Char(
        compute="_compute_address_complete",
        store=False,
        help="Address formatted for display in map view",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("scheduled", "Scheduled"),
            ("delivered", "Delivered"),
            ("skipped", "Skipped"),
        ],
        default="draft",
    )

    @api.depends("partner_id", "order_id", "sequence")
    def _compute_display_name(self):
        for stop in self:
            if stop.partner_id:
                name_parts = []
                if stop.order_id:
                    name_parts.append(stop.order_id.name)
                name_parts.append(f"Stop {stop.sequence}")
                name_parts.append(stop.partner_id.display_name)
                stop.display_name = " - ".join(name_parts)
            else:
                stop.display_name = f"Stop {stop.id}"

    @api.depends("partner_id")
    def _compute_address_complete(self):
        for stop in self:
            if stop.partner_id:
                address_parts = []
                if stop.partner_id.street:
                    address_parts.append(stop.partner_id.street)
                if stop.partner_id.street2:
                    address_parts.append(stop.partner_id.street2)
                if stop.partner_id.city:
                    address_parts.append(stop.partner_id.city)
                if stop.partner_id.state_id:
                    address_parts.append(stop.partner_id.state_id.name)
                if stop.partner_id.zip:
                    address_parts.append(stop.partner_id.zip)
                if stop.partner_id.country_id:
                    address_parts.append(stop.partner_id.country_id.name)
                address_str = ", ".join(address_parts)
                stop.address_complete = address_str
                stop.display_address = address_str
            else:
                stop.address_complete = ""
                stop.display_address = ""

    def action_open_google_maps(self):
        """
        Open Google Maps in a new tab with route for a single stop.
        Uses the stop's order to get all stops for the route.
        Considers origin_id and destination_id from the order.

        Returns:
            dict: Action to open Google Maps URL
        """
        self.ensure_one()
        if not self.order_id:
            raise UserError(_("Stop must be linked to an order."))

        # Get origin coordinates from order.origin_id if available
        origin_coords = None
        if (
            self.order_id.origin_id
            and self.order_id.origin_id.partner_latitude
            and self.order_id.origin_id.partner_longitude
        ):
            origin_coords = (
                self.order_id.origin_id.partner_latitude,
                self.order_id.origin_id.partner_longitude,
            )

        # Get destination coordinates from order.destination_id if available
        destination_coords = None
        if (
            self.order_id.destination_id
            and self.order_id.destination_id.partner_latitude
            and self.order_id.destination_id.partner_longitude
        ):
            destination_coords = (
                self.order_id.destination_id.partner_latitude,
                self.order_id.destination_id.partner_longitude,
            )

        # Collect stop coordinates
        stop_coordinates = []
        for stop in self.order_id.stop_ids.sorted("sequence"):
            if stop.latitude and stop.longitude:
                stop_coordinates.append((stop.latitude, stop.longitude))

        url = self._generate_google_maps_url(
            stop_coordinates, origin_coords, destination_coords
        )
        if not url:
            raise UserError(_("Could not generate Google Maps URL."))

        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "new",
        }

    def action_open_google_maps_multi(self):
        """
        Open Google Maps in a new tab with route for multiple selected stops.
        Considers origin_id and destination_id from the order if available.

        Returns:
            dict: Action to open Google Maps URL
        """
        # Get origin coordinates from order.origin_id if available
        origin_coords = None
        destination_coords = None

        # Try to get order from first stop
        order = self[0].order_id if self and self[0].order_id else None
        if order:
            if (
                order.origin_id
                and order.origin_id.partner_latitude
                and order.origin_id.partner_longitude
            ):
                origin_coords = (
                    order.origin_id.partner_latitude,
                    order.origin_id.partner_longitude,
                )
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
        for stop in self.sorted("sequence"):
            if stop.latitude and stop.longitude:
                stop_coordinates.append((stop.latitude, stop.longitude))

        url = self._generate_google_maps_url(
            stop_coordinates, origin_coords, destination_coords
        )
        if not url:
            raise UserError(_("Could not generate Google Maps URL."))

        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "new",
        }

    @staticmethod
    def _generate_google_maps_url(
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
