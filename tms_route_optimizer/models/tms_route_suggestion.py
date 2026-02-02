from odoo import _, api, fields, models
from odoo.exceptions import UserError


class TMSRouteSuggestion(models.Model):
    """Route suggestion awaiting user approval."""

    _name = "tms.route.suggestion"
    _description = "TMS Route Suggestion"
    _order = "planning_date, id"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(required=True, tracking=True)
    config_id = fields.Many2one(
        "tms.route.optimizer.config",
        string="Configuration",
        required=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        related="config_id.company_id",
        store=True,
        string="Company",
    )
    team_id = fields.Many2one(
        related="config_id.team_id",
        store=True,
        string="Team",
    )
    suggestion_date = fields.Date(
        default=fields.Date.today,
        help="Date when this suggestion was created",
    )
    planning_date = fields.Date(
        required=True,
        string="Route Date",
        help="Planned date for this route",
        tracking=True,
    )
    state = fields.Selection(
        [
            ("suggested", "Suggested"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("expired", "Expired"),
        ],
        default="suggested",
        required=True,
        tracking=True,
    )

    # Vehicle assignment
    vehicle_id = fields.Many2one(
        "fleet.vehicle",
        string="Vehicle",
        tracking=True,
    )
    vehicle_type_id = fields.Many2one(
        "fleet.vehicle.type",
        string="Vehicle Type",
        tracking=True,
    )

    # Stops
    stop_ids = fields.Many2many(
        "tms.order.stop",
        "tms_route_suggestion_stop_rel",
        "suggestion_id",
        "stop_id",
        string="Delivery Stops",
    )
    stop_count = fields.Integer(
        compute="_compute_stop_count",
        string="Stops",
    )

    # Route metrics
    total_distance = fields.Float(
        string="Total Distance (km)",
        tracking=True,
    )
    total_cost = fields.Float(tracking=True)
    total_weight = fields.Float(
        string="Total Weight (kg)",
    )
    total_volume = fields.Float(
        string="Total Volume (m³)",
    )
    total_packages = fields.Integer(
        compute="_compute_total_packages",
    )
    google_maps_url = fields.Char(
        string="Google Maps URL",
    )

    # Created order after approval
    order_id = fields.Many2one(
        "tms.order",
        string="Created Order",
        readonly=True,
        tracking=True,
    )

    @api.depends("stop_ids")
    def _compute_stop_count(self):
        for suggestion in self:
            suggestion.stop_count = len(suggestion.stop_ids)

    @api.depends("stop_ids.package_count")
    def _compute_total_packages(self):
        for suggestion in self:
            suggestion.total_packages = sum(suggestion.stop_ids.mapped("package_count"))

    def action_approve(self):
        """Approve the suggestion and create a TMS order."""
        self.ensure_one()

        if self.state != "suggested":
            raise UserError(_("Only suggested routes can be approved."))

        # Determine vehicle
        vehicle = self.vehicle_id
        if not vehicle and self.vehicle_type_id:
            # Find available vehicle of the type
            vehicle = self._get_available_vehicle_for_type()

        if not vehicle:
            raise UserError(
                _("No vehicle available for this route. Please select a vehicle first.")
            )

        # Create the TMS order
        order = self._create_order_from_suggestion(vehicle)

        # Update suggestion state
        self.write(
            {
                "state": "approved",
                "order_id": order.id,
                "vehicle_id": vehicle.id,
            }
        )

        # Update stop states
        self.stop_ids.write({"state": "scheduled"})

        return {
            "type": "ir.actions.act_window",
            "name": _("Created Order"),
            "res_model": "tms.order",
            "res_id": order.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_reject(self):
        """Reject the suggestion. Stops remain in draft for next calculation."""
        self.ensure_one()

        if self.state != "suggested":
            raise UserError(_("Only suggested routes can be rejected."))

        self.write({"state": "rejected"})

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Suggestion Rejected"),
                "message": _(
                    "The route suggestion has been rejected. "
                    "Stops will be included in the next optimization."
                ),
                "type": "warning",
            },
        }

    def _get_available_vehicle_for_type(self):
        """Find an available vehicle of the specified type."""
        self.ensure_one()

        if not self.vehicle_type_id:
            return False

        domain = [
            ("vehicle_type_id", "=", self.vehicle_type_id.id),
        ]

        # Filter by team if available
        if self.team_id:
            domain.append(("tms_team_id", "=", self.team_id.id))

        return self.env["fleet.vehicle"].search(domain, limit=1)

    def _create_order_from_suggestion(self, vehicle):
        """Create a TMS order from this suggestion."""
        self.ensure_one()

        # Get the depot (origin) from the team or first stop
        origin = False
        if self.team_id and hasattr(self.team_id, "depot_id"):
            origin = self.team_id.depot_id

        vals = {
            "vehicle_id": vehicle.id,
            "tms_team_id": self.team_id.id if self.team_id else False,
            "scheduled_date_start": fields.Datetime.from_string(
                str(self.planning_date) + " 08:00:00"
            ),
            "origin_id": origin.id if origin else False,
        }

        # Add driver if vehicle has one
        if vehicle.tms_driver_id:
            vals["driver_id"] = vehicle.tms_driver_id.id

        order = self.env["tms.order"].create(vals)

        # Associate stops with the order
        if self.stop_ids:
            self.stop_ids.write({"order_id": order.id})

        return order

    def action_view_on_map(self):
        """Open the Google Maps URL for this route."""
        self.ensure_one()

        if not self.google_maps_url:
            raise UserError(_("No map URL available for this route."))

        return {
            "type": "ir.actions.act_url",
            "url": self.google_maps_url,
            "target": "new",
        }

    def action_select_vehicle(self):
        """Open a wizard to select a vehicle for this suggestion."""
        self.ensure_one()

        if self.state != "suggested":
            raise UserError(_("Vehicle can only be selected for suggested routes."))

        # Return an action that opens vehicle selection
        return {
            "type": "ir.actions.act_window",
            "name": _("Select Vehicle"),
            "res_model": "fleet.vehicle",
            "view_mode": "list",
            "target": "new",
            "domain": [("tms_team_id", "=", self.team_id.id)] if self.team_id else [],
            "context": {
                "suggestion_id": self.id,
            },
        }
