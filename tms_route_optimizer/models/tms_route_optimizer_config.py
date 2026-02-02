import logging
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class TMSRouteOptimizerConfig(models.Model):
    """Configuration for automatic route optimization."""

    _name = "tms.route.optimizer.config"
    _description = "TMS Route Optimizer Configuration"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    team_id = fields.Many2one(
        "tms.team",
        required=True,
        string="Team",
        help="Team whose stops will be optimized",
        tracking=True,
    )

    # Start and end locations
    start_location_id = fields.Many2one(
        "res.partner",
        string="Start Location",
        domain="[('tms_location', '=', True)]",
        context={"default_tms_location": True},
        help="Starting location for route optimization (uses team default if not set)",
        tracking=True,
    )
    end_location_id = fields.Many2one(
        "res.partner",
        string="End Location",
        domain="[('tms_location', '=', True)]",
        context={"default_tms_location": True},
        help="Ending location for route optimization (optional)",
        tracking=True,
    )

    # Planning mode configuration
    planning_mode = fields.Selection(
        [
            ("team", "By Team"),
            ("vehicles", "By Specific Vehicles"),
            ("vehicle_types", "By Vehicle Types"),
        ],
        default="team",
        required=True,
        tracking=True,
    )
    vehicle_ids = fields.Many2many(
        "fleet.vehicle",
        "tms_optimizer_config_vehicle_rel",
        "config_id",
        "vehicle_id",
        string="Vehicles",
    )
    vehicle_type_ids = fields.Many2many(
        "fleet.vehicle.type",
        "tms_optimizer_config_vehicle_type_rel",
        "config_id",
        "vehicle_type_id",
        string="Vehicle Types",
    )
    vehicles_per_type = fields.Integer(
        default=5,
        string="Vehicles per Type",
    )

    # Optimization parameters
    optimization_speed = fields.Selection(
        [
            ("fast", "Rapido (menos de 1 minuto)"),
            ("balanced", "Balanceado (1-2 minutos)"),
            ("quality", "Qualidade Maxima (ate 5 minutos)"),
        ],
        default="balanced",
        required=True,
        tracking=True,
    )
    max_stops_per_vehicle = fields.Integer(
        default=0,
        string="Max Stops per Vehicle",
        help="Maximum number of stops per vehicle (0 = unlimited)",
        tracking=True,
    )
    enable_multi_day = fields.Boolean(
        default=True,
        string="Enable Multi-day Planning",
        tracking=True,
    )
    planning_horizon_days = fields.Integer(
        default=3,
        string="Planning Horizon (days)",
        tracking=True,
    )

    # Scheduling
    cron_hour = fields.Integer(
        default=22,
        string="Execution Hour",
        help="Hour of day when automatic optimization runs (0-23)",
        tracking=True,
    )
    cron_minute = fields.Integer(
        default=0,
        string="Execution Minute",
        help="Minute of hour when automatic optimization runs (0-59)",
        tracking=True,
    )

    # Stop filtering
    days_ahead = fields.Integer(
        default=3,
        help="Fetch stops scheduled for the next N days",
        tracking=True,
    )

    # Related suggestions
    suggestion_ids = fields.One2many(
        "tms.route.suggestion",
        "config_id",
        string="Suggestions",
    )
    suggestion_count = fields.Integer(
        compute="_compute_suggestion_count",
        string="Total Suggestions",
    )
    pending_suggestion_count = fields.Integer(
        compute="_compute_suggestion_count",
        string="Pending Suggestions",
    )

    @api.depends("suggestion_ids", "suggestion_ids.state")
    def _compute_suggestion_count(self):
        for config in self:
            config.suggestion_count = len(config.suggestion_ids)
            config.pending_suggestion_count = len(
                config.suggestion_ids.filtered(lambda s: s.state == "suggested")
            )

    @api.constrains("cron_hour")
    def _check_cron_hour(self):
        for config in self:
            if not 0 <= config.cron_hour <= 23:
                raise UserError(_("Execution hour must be between 0 and 23"))

    @api.constrains("cron_minute")
    def _check_cron_minute(self):
        for config in self:
            if not 0 <= config.cron_minute <= 59:
                raise UserError(_("Execution minute must be between 0 and 59"))

    @api.model
    def _run_scheduled_optimization(self):
        """Called by cron job to run all active optimizations."""
        configs = self.search([("active", "=", True)])

        for config in configs:
            try:
                config._run_auto_optimization()
            except Exception as e:
                _logger.error(
                    "Error in automatic optimization %s: %s", config.name, str(e)
                )

    def _run_auto_optimization(self):
        """Execute automatic optimization for this configuration."""
        self.ensure_one()

        # 1. Expire old suggestions that weren't approved
        self._expire_old_suggestions()

        # 2. Get eligible stops
        stops = self._get_eligible_stops()
        if not stops:
            _logger.info(
                "No eligible stops found for optimization config %s", self.name
            )
            return

        _logger.info(
            "Running automatic optimization %s with %d stops",
            self.name,
            len(stops),
        )

        # 3. Create and run the optimizer wizard
        wizard = self.env["tms.route.optimizer"].create(
            {
                "name": _("Auto: %(name)s - %(date)s")
                % {
                    "name": self.name,
                    "date": fields.Date.today(),
                },
                "team_id": self.team_id.id,
                "start_location_id": self.start_location_id.id,
                "end_location_id": self.end_location_id.id
                if self.end_location_id
                else False,
                "planning_mode": self.planning_mode,
                "vehicle_ids": [(6, 0, self.vehicle_ids.ids)],
                "vehicle_type_ids": [(6, 0, self.vehicle_type_ids.ids)],
                "vehicles_per_type": self.vehicles_per_type,
                "optimization_speed": self.optimization_speed,
                "max_stops_per_vehicle": self.max_stops_per_vehicle,
                "enable_multi_day": self.enable_multi_day,
                "planning_horizon_days": self.planning_horizon_days,
                "delivery_stop_ids": [(6, 0, stops.ids)],
                "optimization_date": fields.Date.today(),
            }
        )

        try:
            wizard.action_run_optimization()

            if wizard.state == "done":
                # 4. Convert results to suggestions
                self._create_suggestions_from_results(wizard)
                _logger.info(
                    "Automatic optimization %s completed successfully", self.name
                )
            else:
                _logger.warning(
                    "Automatic optimization %s finished with state %s: %s",
                    self.name,
                    wizard.state,
                    wizard.error_message,
                )
        except Exception as e:
            _logger.error("Optimization %s failed: %s", self.name, str(e))
            raise

    def _expire_old_suggestions(self):
        """Mark old non-approved suggestions as expired."""
        old_suggestions = self.env["tms.route.suggestion"].search(
            [
                ("config_id", "=", self.id),
                ("state", "=", "suggested"),
            ]
        )
        if old_suggestions:
            old_suggestions.write({"state": "expired"})
            _logger.info(
                "Expired %d old suggestions for config %s",
                len(old_suggestions),
                self.name,
            )

    def _get_eligible_stops(self):
        """Get stops eligible for automatic optimization."""
        self.ensure_one()

        date_limit = fields.Date.today() + timedelta(days=self.days_ahead)

        # Search for draft stops within the date range
        domain = [
            ("state", "=", "draft"),
            ("scheduled_date", "<=", date_limit),
        ]

        # Filter by team - depends on how stops are linked to teams
        # Check if the stop's related order has the team
        stops = self.env["tms.order.stop"].search(domain)

        # Filter by team if available
        if self.team_id:
            stops = stops.filtered(
                lambda s: not s.order_id or s.order_id.tms_team_id == self.team_id
            )

        return stops

    def _create_suggestions_from_results(self, wizard):
        """Create route suggestions from optimizer results."""
        self.ensure_one()
        Suggestion = self.env["tms.route.suggestion"]

        for result in wizard.result_ids:
            if not result.stop_ids:
                continue

            # Determine planning date from day result or wizard
            planning_date = result.planning_date or wizard.optimization_date

            vehicle_name = (
                result.vehicle_id.name
                if result.vehicle_id
                else result.vehicle_type_id.name
            )
            Suggestion.create(
                {
                    "name": _("Route suggestion: %(vehicle)s - %(date)s")
                    % {
                        "vehicle": vehicle_name,
                        "date": planning_date,
                    },
                    "config_id": self.id,
                    "suggestion_date": fields.Date.today(),
                    "planning_date": planning_date,
                    "vehicle_id": result.vehicle_id.id if result.vehicle_id else False,
                    "vehicle_type_id": result.vehicle_type_id.id
                    if result.vehicle_type_id
                    else False,
                    "stop_ids": [(6, 0, result.stop_ids.ids)],
                    "total_distance": result.total_distance,
                    "total_cost": result.route_cost,
                    "total_weight": result.total_weight,
                    "total_volume": result.total_volume,
                    "google_maps_url": result.google_maps_url,
                }
            )

    def action_run_now(self):
        """Button to manually run optimization."""
        self.ensure_one()
        self._run_auto_optimization()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Optimization Complete"),
                "message": _("Route optimization has been executed."),
                "type": "success",
            },
        }

    def action_view_suggestions(self):
        """Open suggestions list for this config."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Route Suggestions"),
            "res_model": "tms.route.suggestion",
            "view_mode": "list,form",
            "domain": [("config_id", "=", self.id)],
            "context": {"default_config_id": self.id},
        }
