from odoo import _, api, fields, models
from odoo.exceptions import UserError


class TMSOrderStop(models.Model):
    _name = "tms.order.stop"
    _description = "TMS Order Delivery Stop"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "order_id, stop_type_order, sequence"

    # Mapping for stop_type sort order: origin=0, delivery=1, destination=2
    STOP_TYPE_ORDER = {"origin": 0, "delivery": 1, "destination": 2}

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
    stop_type = fields.Selection(
        [
            ("origin", "Origin/Pickup"),
            ("delivery", "Delivery"),
            ("destination", "Destination/Return"),
        ],
        default="delivery",
        required=True,
        index=True,
        help="Type of stop: origin (pickup point), delivery (normal stop), "
        "or destination (return/final point)",
    )
    stop_type_order = fields.Integer(
        compute="_compute_stop_type_order",
        store=True,
        index=True,
        help="Numeric order for stop_type: 0=origin, 1=delivery, 2=destination",
    )
    sequence = fields.Integer(
        default=10,
        help="Order of the stop in the route",
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Delivery Partner",
        required=False,
        help="Recipient of the delivery (for delivery stops)",
    )
    location_id = fields.Many2one(
        "res.partner",
        string="TMS Location",
        domain="[('tms_location', '=', True)]",
        help="TMS location for origin/destination stops",
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
        compute="_compute_coordinates",
        store=True,
        readonly=True,
    )
    longitude = fields.Float(
        compute="_compute_coordinates",
        store=True,
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

    @api.constrains("stop_type", "order_id")
    def _check_unique_endpoint_per_order(self):
        """Ensure each order has at most one origin and one destination stop."""
        for stop in self:
            if stop.order_id and stop.stop_type in ("origin", "destination"):
                count = self.search_count(
                    [
                        ("order_id", "=", stop.order_id.id),
                        ("stop_type", "=", stop.stop_type),
                        ("id", "!=", stop.id),
                    ]
                )
                if count > 0:
                    type_label = (
                        _("origin") if stop.stop_type == "origin" else _("destination")
                    )
                    raise UserError(
                        _(
                            "Order %(order)s already has a"
                            " %(type)s stop. Each order can"
                            " have only one %(type)s."
                        )
                        % {
                            "order": stop.order_id.name,
                            "type": type_label,
                        }
                    )

    @api.constrains("stop_type", "partner_id", "location_id")
    def _check_partner_or_location(self):
        """Validate partner_id for delivery and location_id
        for origin/destination stops."""
        for stop in self:
            if stop.stop_type == "delivery" and not stop.partner_id:
                raise UserError(
                    _("Delivery stops must have a Delivery Partner specified.")
                )
            if stop.stop_type in ("origin", "destination") and not stop.location_id:
                raise UserError(
                    _("Origin/Destination stops must have a TMS Location specified.")
                )

    @api.depends("stop_type")
    def _compute_stop_type_order(self):
        """Compute numeric order for stop_type to enable correct SQL ordering."""
        for stop in self:
            stop.stop_type_order = self.STOP_TYPE_ORDER.get(stop.stop_type, 1)

    @api.onchange("stop_type")
    def _onchange_stop_type(self):
        """Set default sequence based on stop_type."""
        if self.stop_type == "origin":
            self.sequence = 0
        elif self.stop_type == "destination":
            self.sequence = 9999

    @api.depends(
        "partner_id.partner_latitude",
        "partner_id.partner_longitude",
        "location_id.partner_latitude",
        "location_id.partner_longitude",
        "stop_type",
    )
    def _compute_coordinates(self):
        """Compute coordinates from partner_id or location_id based on stop_type."""
        for stop in self:
            if stop.stop_type in ("origin", "destination") and stop.location_id:
                stop.latitude = stop.location_id.partner_latitude or 0.0
                stop.longitude = stop.location_id.partner_longitude or 0.0
            elif stop.partner_id:
                stop.latitude = stop.partner_id.partner_latitude or 0.0
                stop.longitude = stop.partner_id.partner_longitude or 0.0
            else:
                stop.latitude = 0.0
                stop.longitude = 0.0

    @api.depends("partner_id", "location_id", "order_id", "sequence", "stop_type")
    def _compute_display_name(self):
        stop_type_labels = {
            "origin": _("Origin"),
            "destination": _("Destination"),
            "delivery": _("Stop"),
        }
        for stop in self:
            partner = (
                stop.location_id if stop.stop_type != "delivery" else stop.partner_id
            )
            if partner:
                name_parts = []
                if stop.order_id:
                    name_parts.append(stop.order_id.name)
                type_label = stop_type_labels.get(stop.stop_type, _("Stop"))
                if stop.stop_type == "delivery":
                    name_parts.append(f"{type_label} {stop.sequence}")
                else:
                    name_parts.append(type_label)
                name_parts.append(partner.display_name)
                stop.display_name = " - ".join(name_parts)
            else:
                stop.display_name = f"Stop {stop.id}"

    @api.depends("partner_id", "location_id", "stop_type")
    def _compute_address_complete(self):
        for stop in self:
            # Use location_id for origin/destination, partner_id for delivery
            partner = (
                stop.location_id
                if stop.stop_type in ("origin", "destination")
                else stop.partner_id
            )
            if partner:
                address_parts = []
                if partner.street:
                    address_parts.append(partner.street)
                if partner.street2:
                    address_parts.append(partner.street2)
                if partner.city:
                    address_parts.append(partner.city)
                if partner.state_id:
                    address_parts.append(partner.state_id.name)
                if partner.zip:
                    address_parts.append(partner.zip)
                if partner.country_id:
                    address_parts.append(partner.country_id.name)
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
        Now uses stop_type to determine origin/destination from stops.

        Returns:
            dict: Action to open Google Maps URL
        """
        self.ensure_one()
        if not self.order_id:
            raise UserError(_("Stop must be linked to an order."))

        # Get all stops sorted by stop_type and sequence
        all_stops = self.order_id.stop_ids.sorted(lambda s: (s.stop_type, s.sequence))
        url = self._generate_google_maps_url_from_stops(all_stops)

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
        Uses stop_type to determine origin/destination.

        Returns:
            dict: Action to open Google Maps URL
        """
        # Sort stops by stop_type and sequence
        sorted_stops = self.sorted(lambda s: (s.stop_type, s.sequence))
        url = self._generate_google_maps_url_from_stops(sorted_stops)

        if not url:
            raise UserError(_("Could not generate Google Maps URL."))

        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "new",
        }

    def _generate_google_maps_url_from_stops(self, stops):
        """
        Generate Google Maps URL from a recordset of stops.
        Uses stop_type to determine origin and destination.

        Args:
            stops: Recordset of tms.order.stop sorted by stop_type and sequence

        Returns:
            Google Maps URL string or None if insufficient coordinates
        """
        # Find origin, delivery stops, and destination
        origin_stop = stops.filtered(lambda s: s.stop_type == "origin")[:1]
        destination_stop = stops.filtered(lambda s: s.stop_type == "destination")[:1]
        delivery_stops = stops.filtered(lambda s: s.stop_type == "delivery")

        # Collect coordinates
        all_coords = []

        # Add origin if exists
        if origin_stop and origin_stop.latitude and origin_stop.longitude:
            all_coords.append((origin_stop.latitude, origin_stop.longitude))

        # Add delivery stops
        for stop in delivery_stops.sorted("sequence"):
            if stop.latitude and stop.longitude:
                all_coords.append((stop.latitude, stop.longitude))

        # Add destination if exists
        if (
            destination_stop
            and destination_stop.latitude
            and destination_stop.longitude
        ):
            all_coords.append((destination_stop.latitude, destination_stop.longitude))

        if len(all_coords) < 2:
            return None

        # First coord is origin, last is destination, rest are waypoints
        origin = f"{all_coords[0][0]},{all_coords[0][1]}"
        destination = f"{all_coords[-1][0]},{all_coords[-1][1]}"

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
    def _generate_google_maps_url(
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
