import json
import time
from datetime import datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .tms_route_optimizer_ortools import RouteOptimizerHelper

SPEED_MODE_CONFIG = {
    "fast": {
        "first_solution_strategy": "PARALLEL_CHEAPEST_INSERTION",
        "local_search_metaheuristic": "GREEDY_DESCENT",
        "max_time_seconds": 30,
        "solution_limit": 1,
    },
    "balanced": {
        "first_solution_strategy": "SAVINGS",
        "local_search_metaheuristic": "SIMULATED_ANNEALING",
        "max_time_seconds": 120,
        "solution_limit": 5,
    },
    "quality": {
        "first_solution_strategy": "PATH_CHEAPEST_ARC",
        "local_search_metaheuristic": "GUIDED_LOCAL_SEARCH",
        "max_time_seconds": 300,
        "solution_limit": 0,
    },
}


class TMSRouteOptimizer(models.TransientModel):
    _name = "tms.route.optimizer"
    _description = "TMS Route Optimizer Wizard"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(
        default=lambda self: (
            f"Optimization {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        ),
    )
    # Planning mode selection
    planning_mode = fields.Selection(
        [
            ("team", "By Team"),
            ("vehicles", "By Specific Vehicles"),
            ("vehicle_types", "By Vehicle Types"),
        ],
        default="team",
        required=True,
        help="Select how to choose vehicles for optimization",
    )
    team_id = fields.Many2one(
        "tms.team",
        string="Team",
        required=True,
    )
    # Start and end locations
    start_location_id = fields.Many2one(
        "res.partner",
        string="Start Location",
        domain="[('tms_location', '=', True)]",
        context={"default_tms_location": True},
        help="Starting location for route optimization (uses team default if not set)",
    )
    end_location_id = fields.Many2one(
        "res.partner",
        string="End Location",
        domain="[('tms_location', '=', True)]",
        context={"default_tms_location": True},
        help="Ending location for route optimization (optional)",
    )
    # For "By Specific Vehicles" mode
    vehicle_ids = fields.Many2many(
        "fleet.vehicle",
        "tms_route_optimizer_vehicle_rel",
        "optimizer_id",
        "vehicle_id",
        string="Vehicles",
        help="Specific vehicles to use for optimization",
    )
    # For "By Vehicle Types" mode
    vehicle_type_ids = fields.Many2many(
        "fleet.vehicle.type",
        "tms_route_optimizer_vehicle_type_rel",
        "optimizer_id",
        "vehicle_type_id",
        string="Vehicle Types",
        help="Types of vehicles to use for optimization",
    )
    vehicles_per_type = fields.Integer(
        default=5,
        string="Vehicles per Type",
        help="Number of virtual vehicles to create per vehicle type",
    )
    # Max stops constraint
    max_stops_per_vehicle = fields.Integer(
        default=0,
        string="Max Stops per Vehicle",
        help="Maximum number of stops per vehicle. 0 means no limit.",
    )
    # Multi-day planning
    enable_multi_day = fields.Boolean(
        default=False,
        string="Enable Multi-Day Planning",
        help="Allow optimization to span multiple days if capacity is exceeded",
    )
    planning_horizon_days = fields.Integer(
        default=3,
        string="Planning Horizon (days)",
        help="Number of days to consider for multi-day optimization",
    )
    day_result_ids = fields.One2many(
        "tms.route.optimizer.day.result",
        "optimizer_id",
        string="Daily Results",
    )
    # Recalculation options
    recalculation_mode = fields.Selection(
        [
            ("new", "New Optimization"),
            ("merge", "Merge with Pending Trips"),
        ],
        default="new",
        string="Mode",
        help="'New' creates fresh routes. "
        "'Merge' adds stops to existing pending trips.",
    )
    include_pending_orders = fields.Boolean(
        default=False,
        help="Include stops from pending (non-executed) orders in optimization",
    )
    pending_order_ids = fields.Many2many(
        "tms.order",
        "tms_route_optimizer_pending_order_rel",
        "optimizer_id",
        "order_id",
        string="Available Pending Orders",
        compute="_compute_pending_orders",
        store=False,
    )
    selected_pending_order_ids = fields.Many2many(
        "tms.order",
        "tms_route_optimizer_selected_pending_order_rel",
        "optimizer_id",
        "order_id",
        string="Orders to Recalculate",
    )
    date_from = fields.Datetime(
        required=True,
        default=fields.Datetime.now,
    )
    date_to = fields.Datetime(
        required=True,
        default=fields.Datetime.now,
    )
    delivery_stop_ids = fields.Many2many(
        "tms.order.stop",
        string="Delivery Stops",
        help="Stops to optimize (auto-filled based on date range)",
    )
    optimization_date = fields.Date(
        required=True,
        default=fields.Date.today,
    )
    optimization_speed = fields.Selection(
        [
            ("fast", "Rapido (menos de 1 minuto)"),
            ("balanced", "Balanceado (1-2 minutos)"),
            ("quality", "Qualidade Maxima (ate 5 minutos)"),
        ],
        default="balanced",
        required=True,
        help=(
            "Rapido: solucao em segundos, boa para testes. "
            "Balanceado: melhor relacao tempo/qualidade. "
            "Qualidade: busca exaustiva, ideal para rotas criticas."
        ),
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("optimizing", "Optimizing"),
            ("done", "Done"),
            ("error", "Error"),
        ],
        default="draft",
    )
    optimization_result = fields.Text(
        string="Optimization Result (JSON)",
    )
    total_cost = fields.Float()
    total_distance = fields.Float(
        string="Total Distance (km)",
    )
    total_vehicles_used = fields.Integer()
    optimization_time = fields.Float(
        string="Optimization Time (seconds)",
    )
    result_ids = fields.One2many(
        "tms.route.optimizer.result",
        "optimizer_id",
        string="Results",
    )
    error_message = fields.Text()

    def _get_origin_location(self):
        """Get origin location with priority:
        start_location_id -> team -> company default
        """
        if self.start_location_id:
            return self.start_location_id
        if self.team_id and self.team_id.default_origin_location_id:
            return self.team_id.default_origin_location_id
        # Get company-dependent default
        company = self.env.company
        if company.tms_default_origin_location_id:
            return company.tms_default_origin_location_id
        return False

    def _get_destination_location(self):
        """Get destination location with priority:
        end_location_id -> start_location_id -> team -> company default -> origin
        """
        if self.end_location_id:
            return self.end_location_id
        if self.start_location_id:
            return self.start_location_id
        if self.team_id and self.team_id.default_destination_location_id:
            return self.team_id.default_destination_location_id
        # Get company-dependent default
        company = self.env.company
        if company.tms_default_destination_location_id:
            return company.tms_default_destination_location_id
        # Fallback to origin if no destination configured
        return self._get_origin_location()

    @api.onchange("team_id", "date_from", "date_to")
    def _onchange_dates(self):
        """Auto-fill delivery stops based on date range"""
        if self.team_id and self.date_from and self.date_to:
            stops = self.env["tms.order.stop"].search(
                [
                    ("scheduled_date", ">=", self.date_from),
                    ("scheduled_date", "<=", self.date_to),
                    ("order_id.tms_team_id", "=", self.team_id.id),
                    ("state", "=", "draft"),
                ]
            )
            self.delivery_stop_ids = stops

    @api.depends("team_id")
    def _compute_pending_orders(self):
        """Find orders that can be recalculated (not yet executed)"""
        for wizard in self:
            if wizard.team_id:
                # Find orders with stops in non-delivered state that can be recalculated
                pending_orders = self.env["tms.order"].search(
                    [
                        ("tms_team_id", "=", wizard.team_id.id),
                        ("stage_id.is_completed", "=", False),
                        ("is_locked_for_optimization", "=", False),
                    ]
                )
                # Filter to only include orders where no stops are delivered
                recalculable_orders = pending_orders.filtered(
                    lambda o: not any(s.state == "delivered" for s in o.stop_ids)
                )
                wizard.pending_order_ids = recalculable_orders
            else:
                wizard.pending_order_ids = self.env["tms.order"]

    def _prepare_merge_stops(self):
        """
        Prepare stops for merge mode: collect stops from selected pending orders
        and combine with new stops.
        """
        if not self.selected_pending_order_ids:
            return

        # Collect stops from selected pending orders
        existing_stops = self.env["tms.order.stop"]
        for order in self.selected_pending_order_ids:
            # Reset stops to draft state so they can be re-optimized
            order.stop_ids.filtered(lambda s: s.state == "scheduled").write(
                {"state": "draft"}
            )
            # Collect all draft stops from these orders
            existing_stops |= order.stop_ids.filtered(lambda s: s.state == "draft")

        # Combine with new stops
        all_stops = existing_stops | self.delivery_stop_ids
        self.delivery_stop_ids = all_stops

    def _validate_optimization_data(self):
        """Validate data before optimization"""
        if not self.delivery_stop_ids:
            raise UserError(_("No delivery stops to optimize"))

        # Check geolocation
        for stop in self.delivery_stop_ids:
            if not stop.latitude or not stop.longitude:
                raise UserError(
                    _("Stop %s has no geolocation coordinates") % stop.partner_id.name
                )

    def _validate_origin_location(self):
        """Validate and return origin location"""
        origin_location = self._get_origin_location()
        if not origin_location:
            if self.start_location_id:
                raise UserError(
                    _(
                        "Start location '%s' has no geolocation coordinates. "
                        "Please configure latitude and longitude."
                    )
                    % self.start_location_id.name
                )
            raise UserError(
                _(
                    "Origin location not configured. "
                    "Please set start location or default origin location "
                    "in team or settings."
                )
            )
        if (
            not origin_location.partner_latitude
            or not origin_location.partner_longitude
        ):
            raise UserError(
                _(
                    "Origin location '%s' has no geolocation coordinates. "
                    "Please configure latitude and longitude."
                )
                % origin_location.name
            )
        return origin_location

    def _validate_end_location(self):
        """Validate end location if provided"""
        if self.end_location_id:
            if (
                not self.end_location_id.partner_latitude
                or not self.end_location_id.partner_longitude
            ):
                raise UserError(
                    _(
                        "End location '%s' has no geolocation coordinates. "
                        "Please configure latitude and longitude."
                    )
                    % self.end_location_id.name
                )
            return self.end_location_id
        return False

    def _get_vehicles_for_optimization(self):
        """Get vehicles based on planning mode"""
        if self.planning_mode == "team":
            return self._get_vehicles_by_team()
        elif self.planning_mode == "vehicles":
            return self._get_vehicles_by_selection()
        elif self.planning_mode == "vehicle_types":
            # For vehicle_types mode, we return None here
            # and use _prepare_vehicle_data_from_types() instead
            return None
        raise UserError(_("Invalid planning mode"))

    def _get_vehicles_by_team(self):
        """Get vehicles for team, filtered by allowed vehicle types"""
        vehicle_domain = [("tms_team_id", "=", self.team_id.id)]
        if self.team_id.allowed_vehicle_type_ids:
            vehicle_domain.append(
                ("vehicle_type_id", "in", self.team_id.allowed_vehicle_type_ids.ids)
            )
        vehicles = self.env["fleet.vehicle"].search(vehicle_domain)
        if not vehicles:
            raise UserError(_("No vehicles available for this team"))
        return vehicles

    def _get_vehicles_by_selection(self):
        """Get user-selected specific vehicles"""
        if not self.vehicle_ids:
            raise UserError(_("Please select at least one vehicle"))
        return self.vehicle_ids

    def _prepare_vehicle_data_from_types(self):
        """
        Prepare vehicle data arrays from vehicle types (virtual vehicles).
        Returns capacity and cost arrays plus type mapping for result creation.
        """
        if not self.vehicle_type_ids:
            raise UserError(_("Please select at least one vehicle type"))

        vehicle_capacities_weight = []
        vehicle_capacities_volume = []
        cost_per_km = []
        minimum_trip_cost = []
        type_mapping = []  # Track which type each slot belongs to

        for vtype in self.vehicle_type_ids:
            for _i in range(self.vehicles_per_type):
                vehicle_capacities_weight.append(vtype.default_weight_capacity or 1000)
                vehicle_capacities_volume.append(vtype.default_volume_capacity or 10)
                cost_per_km.append(vtype.default_cost_per_km or 5.0)
                minimum_trip_cost.append(vtype.default_minimum_trip_cost or 100.0)
                type_mapping.append(vtype.id)

        return (
            vehicle_capacities_weight,
            vehicle_capacities_volume,
            cost_per_km,
            minimum_trip_cost,
            type_mapping,
        )

    def _get_vehicle_for_type(self, vehicle_type_id):
        """Find an available vehicle of the specified type for order creation"""
        return self.env["fleet.vehicle"].search(
            [
                ("vehicle_type_id", "=", vehicle_type_id),
                ("tms_team_id", "=", self.team_id.id),
            ],
            limit=1,
        )

    def _prepare_location_data(self, origin_location):
        """Prepare location data for optimization"""
        depot_lat = origin_location.partner_latitude
        depot_lon = origin_location.partner_longitude

        locations = [(depot_lat, depot_lon)]  # Depot is first
        stop_weights = []
        stop_volumes = []
        stop_ids = []

        for stop in self.delivery_stop_ids:
            locations.append((stop.latitude, stop.longitude))
            stop_weights.append(stop.weight or 0)
            stop_volumes.append(stop.volume or 0)
            stop_ids.append(stop.id)

        # Add end location if different from origin
        end_location = self._get_destination_location()
        if end_location and end_location.id != origin_location.id:
            locations.append(
                (end_location.partner_latitude, end_location.partner_longitude)
            )
            # End location has no weight/volume
            stop_weights.append(0)
            stop_volumes.append(0)
            stop_ids.append(None)  # Marker for end location

        return locations, stop_weights, stop_volumes, stop_ids

    def _prepare_vehicle_data(self, vehicles):
        """Prepare vehicle capacity and cost data"""
        vehicle_capacities_weight = []
        vehicle_capacities_volume = []
        cost_per_km = []
        minimum_trip_cost = []

        for vehicle in vehicles:
            vehicle_capacities_weight.append(vehicle.weight_capacity or 1000)
            vehicle_capacities_volume.append(vehicle.volume_capacity or 10)
            cost_per_km.append(vehicle.cost_per_km or 5.0)
            minimum_trip_cost.append(vehicle.minimum_trip_cost or 100.0)

        return (
            vehicle_capacities_weight,
            vehicle_capacities_volume,
            cost_per_km,
            minimum_trip_cost,
        )

    def _compute_distance_matrix(self, locations):
        """Compute distance matrix for a list of locations."""
        return RouteOptimizerHelper.calculate_distance_matrix(locations)

    def _get_speed_config(self):
        """Return OR-Tools config based on optimization_speed."""
        return SPEED_MODE_CONFIG.get(self.optimization_speed, {})

    def _solve_vrp(
        self,
        locations,
        stop_weights,
        stop_volumes,
        vehicle_capacities_weight,
        vehicle_capacities_volume,
        cost_per_km,
        minimum_trip_cost,
        allow_partial_routes=False,
        end_depot=None,
    ):
        """Solve Vehicle Routing Problem"""
        distance_matrix = self._compute_distance_matrix(locations)

        speed_config = self._get_speed_config()
        max_time = speed_config.get("max_time_seconds")
        if max_time is None:
            max_time = float(
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("tms.route_optimizer.max_time_seconds", "300")
            )

        solution = RouteOptimizerHelper.solve_vrp(
            distance_matrix,
            vehicle_capacities_weight,
            vehicle_capacities_volume,
            stop_weights,
            stop_volumes,
            cost_per_km,
            minimum_trip_cost,
            max_time_seconds=max_time,
            max_stops_per_vehicle=self.max_stops_per_vehicle or 0,
            allow_partial_routes=allow_partial_routes,
            end_depot=end_depot,
            first_solution_strategy=speed_config.get("first_solution_strategy"),
            local_search_metaheuristic=speed_config.get("local_search_metaheuristic"),
            solution_limit=speed_config.get("solution_limit", 0),
        )

        if not solution:
            raise UserError(_("No feasible solution found for the given constraints"))

        return solution

    def _store_optimization_results(self, solution, start_time):
        """Store optimization results"""
        self.optimization_result = json.dumps(solution, indent=2)
        self.total_cost = solution["total_cost"]
        self.total_distance = solution["total_distance"]
        self.total_vehicles_used = solution["num_vehicles_used"]
        self.optimization_time = time.time() - start_time

    def _create_result_records(self, solution, vehicles, locations, stop_ids):
        """Create result records for each route"""
        for _route_idx, route in enumerate(solution["routes"]):
            vehicle = vehicles[route["vehicle_id"]]
            route_stops = self._get_route_stops(route, stop_ids)

            result = self._create_result_record(vehicle, route, route_stops)
            self._add_map_urls_to_result(result, route, locations)

    def _get_route_stops(self, route, stop_ids):
        """Get stops in route order"""
        route_stops = []
        for node in route["route"][1:-1]:  # Exclude depot (first and last)
            stop_idx = node - 1  # Convert to stop index (0-based)
            # Skip if this is the end depot (it will have stop_id = None)
            if 0 <= stop_idx < len(stop_ids) and stop_ids[stop_idx] is not None:
                stop_id = stop_ids[stop_idx]
                stop = self.delivery_stop_ids.filtered(
                    lambda s, sid=stop_id: s.id == sid
                )
                if stop:
                    route_stops.append(stop[0])
        return route_stops

    def _create_result_record(self, vehicle, route, route_stops):
        """Create a result record for a route"""
        return self.env["tms.route.optimizer.result"].create(
            {
                "optimizer_id": self.id,
                "vehicle_id": vehicle.id,
                "vehicle_type_id": vehicle.vehicle_type_id.id
                if vehicle.vehicle_type_id
                else False,
                "stop_ids": [(6, 0, [s.id for s in route_stops])],
                "stop_count": len(route_stops),
                "total_distance": route["distance"],
                "total_weight": route["weight"],
                "total_volume": route["volume"],
                "weight_utilization": (
                    (route["weight"] / vehicle.weight_capacity * 100)
                    if vehicle.weight_capacity
                    else 0
                ),
                "volume_utilization": (
                    (route["volume"] / vehicle.volume_capacity * 100)
                    if vehicle.volume_capacity
                    else 0
                ),
                "route_cost": route["cost"],
                "cost_per_km": route["cost"] / route["distance"]
                if route["distance"] > 0
                else 0,
            }
        )

    def _add_map_urls_to_result(self, result, route, locations):
        """Add Google Maps URL to result"""
        route_coords = [locations[node] for node in route["route"]]
        result.google_maps_url = RouteOptimizerHelper.generate_google_maps_url(
            route_coords
        )

        result.route_sequence = json.dumps(
            [{"lat": lat, "lon": lon} for lat, lon in route_coords]
        )

    def _create_result_records_from_types(
        self,
        solution,
        type_mapping,
        locations,
        stop_ids,
        vehicle_capacities_weight,
        vehicle_capacities_volume,
    ):
        """Create result records for vehicle types mode (virtual vehicles)"""
        for _route_idx, route in enumerate(solution["routes"]):
            vehicle_idx = route["vehicle_id"]
            vehicle_type_id = type_mapping[vehicle_idx]
            route_stops = self._get_route_stops(route, stop_ids)

            # Try to find a real vehicle of this type for assignment
            vehicle = self._get_vehicle_for_type(vehicle_type_id)

            # Get capacities for utilization calculation
            weight_capacity = vehicle_capacities_weight[vehicle_idx]
            volume_capacity = vehicle_capacities_volume[vehicle_idx]

            result = self.env["tms.route.optimizer.result"].create(
                {
                    "optimizer_id": self.id,
                    "vehicle_id": vehicle.id if vehicle else False,
                    "vehicle_type_id": vehicle_type_id,
                    "stop_ids": [(6, 0, [s.id for s in route_stops])],
                    "stop_count": len(route_stops),
                    "total_distance": route["distance"],
                    "total_weight": route["weight"],
                    "total_volume": route["volume"],
                    "weight_utilization": (
                        (route["weight"] / weight_capacity * 100)
                        if weight_capacity
                        else 0
                    ),
                    "volume_utilization": (
                        (route["volume"] / volume_capacity * 100)
                        if volume_capacity
                        else 0
                    ),
                    "route_cost": route["cost"],
                    "cost_per_km": route["cost"] / route["distance"]
                    if route["distance"] > 0
                    else 0,
                }
            )
            self._add_map_urls_to_result(result, route, locations)

    def action_run_optimization(self):
        """Run the route optimization"""
        self.state = "optimizing"

        try:
            start_time = time.time()

            # Handle merge mode: collect stops from pending orders
            if self.recalculation_mode == "merge" and self.include_pending_orders:
                self._prepare_merge_stops()

            self._validate_optimization_data()

            if self.enable_multi_day:
                self._run_multi_day_optimization(start_time)
            else:
                self._run_single_day_optimization(start_time)

            self.state = "done"

        except Exception as e:
            self.state = "error"
            self.error_message = str(e)
            raise UserError(_("Optimization failed: %s") % str(e)) from e

    def _run_single_day_optimization(self, start_time):
        """Run optimization for a single day (original behavior)"""
        origin_location = self._validate_origin_location()
        self._validate_end_location()  # Validate end location if provided

        locations, stop_weights, stop_volumes, stop_ids = self._prepare_location_data(
            origin_location
        )

        # Determine end depot index if end location is different from origin
        end_depot = None
        end_location = self._get_destination_location()
        if end_location and end_location.id != origin_location.id:
            # End location is the last element in locations
            end_depot = len(locations) - 1

        # Get vehicles or virtual vehicle data based on planning mode
        vehicles = self._get_vehicles_for_optimization()
        type_mapping = None

        if self.planning_mode == "vehicle_types":
            # Virtual vehicles mode - get data from types
            (
                vehicle_capacities_weight,
                vehicle_capacities_volume,
                cost_per_km,
                minimum_trip_cost,
                type_mapping,
            ) = self._prepare_vehicle_data_from_types()
        else:
            # Real vehicles mode (team or selection)
            (
                vehicle_capacities_weight,
                vehicle_capacities_volume,
                cost_per_km,
                minimum_trip_cost,
            ) = self._prepare_vehicle_data(vehicles)

        solution = self._solve_vrp(
            locations,
            stop_weights,
            stop_volumes,
            vehicle_capacities_weight,
            vehicle_capacities_volume,
            cost_per_km,
            minimum_trip_cost,
            end_depot=end_depot,
        )

        self._store_optimization_results(solution, start_time)

        # Create result records based on planning mode
        if self.planning_mode == "vehicle_types":
            self._create_result_records_from_types(
                solution,
                type_mapping,
                locations,
                stop_ids,
                vehicle_capacities_weight,
                vehicle_capacities_volume,
            )
        else:
            self._create_result_records(solution, vehicles, locations, stop_ids)

    def _run_multi_day_optimization(self, start_time):
        """
        Multi-day optimization strategy:
        1. Start with all stops
        2. Run optimization for day 1 with available vehicles
        3. Collect unassigned stops (if any)
        4. Repeat for day 2, day 3, etc. until all stops are assigned
           or planning horizon is reached
        """
        remaining_stops = self.delivery_stop_ids
        current_date = self.optimization_date
        total_cost = 0
        total_distance = 0
        total_vehicles = 0

        for day_offset in range(self.planning_horizon_days):
            if not remaining_stops:
                break

            planning_date = current_date + timedelta(days=day_offset)

            # Run optimization for remaining stops
            solution, assigned_stops, unassigned_stops = self._optimize_for_day(
                remaining_stops, planning_date
            )

            if solution and solution.get("routes"):
                # Create day result
                self._create_day_result(
                    planning_date, solution, assigned_stops, unassigned_stops
                )

                total_cost += solution["total_cost"]
                total_distance += solution["total_distance"]
                total_vehicles += solution["num_vehicles_used"]

            remaining_stops = unassigned_stops

        # Store aggregated results
        self.total_cost = total_cost
        self.total_distance = total_distance
        self.total_vehicles_used = total_vehicles
        self.optimization_time = time.time() - start_time

        if remaining_stops:
            # Some stops couldn't be assigned within horizon
            self._handle_unassignable_stops(remaining_stops)

    def _optimize_for_day(self, stops, planning_date):
        """Run optimization for a specific day's stops"""
        origin_location = self._validate_origin_location()
        self._validate_end_location()  # Validate end location if provided

        # Prepare location data for these specific stops
        locations, stop_weights, stop_volumes, stop_ids = (
            self._prepare_location_data_for_stops(origin_location, stops)
        )

        # Determine end depot index if end location is different from origin
        end_depot = None
        end_location = self._get_destination_location()
        if end_location and end_location.id != origin_location.id:
            # End location is the last element in locations
            end_depot = len(locations) - 1

        # Get vehicles based on planning mode
        vehicles = self._get_vehicles_for_optimization()
        type_mapping = None

        if self.planning_mode == "vehicle_types":
            (
                vehicle_capacities_weight,
                vehicle_capacities_volume,
                cost_per_km,
                minimum_trip_cost,
                type_mapping,
            ) = self._prepare_vehicle_data_from_types()
        else:
            (
                vehicle_capacities_weight,
                vehicle_capacities_volume,
                cost_per_km,
                minimum_trip_cost,
            ) = self._prepare_vehicle_data(vehicles)

        # Try to solve VRP with partial routes allowed for multi-day planning
        # This allows the solver to leave some stops unvisited when capacity
        # is insufficient, rather than failing completely
        try:
            solution = self._solve_vrp(
                locations,
                stop_weights,
                stop_volumes,
                vehicle_capacities_weight,
                vehicle_capacities_volume,
                cost_per_km,
                minimum_trip_cost,
                allow_partial_routes=True,  # Enable for multi-day planning
                end_depot=end_depot,
            )
        except UserError:
            # No feasible solution at all - even with partial routes
            return None, self.env["tms.order.stop"], stops

        # Identify assigned vs unassigned stops
        # Use unvisited_nodes from solution if available (more reliable)
        if "unvisited_nodes" in solution:
            unvisited_node_indices = set(solution["unvisited_nodes"])
            assigned_stop_ids = set()
            unassigned_stop_ids = set()
            for idx, stop_id in enumerate(stop_ids):
                node_idx = idx + 1  # Node indices are 1-based (0 is depot)
                if node_idx in unvisited_node_indices:
                    unassigned_stop_ids.add(stop_id)
                else:
                    assigned_stop_ids.add(stop_id)
        else:
            # Fallback: extract from routes
            assigned_stop_ids = set()
            for route in solution.get("routes", []):
                for node in route["route"][1:-1]:
                    stop_idx = node - 1
                    if 0 <= stop_idx < len(stop_ids):
                        assigned_stop_ids.add(stop_ids[stop_idx])
            unassigned_stop_ids = set(stop_ids) - assigned_stop_ids

        assigned_stops = stops.filtered(lambda s: s.id in assigned_stop_ids)
        unassigned_stops = stops.filtered(lambda s: s.id in unassigned_stop_ids)

        return solution, assigned_stops, unassigned_stops

    def _prepare_location_data_for_stops(self, origin_location, stops):
        """Prepare location data for specific stops (used in multi-day)"""
        depot_lat = origin_location.partner_latitude
        depot_lon = origin_location.partner_longitude

        locations = [(depot_lat, depot_lon)]  # Depot is first
        stop_weights = []
        stop_volumes = []
        stop_ids = []

        for stop in stops:
            locations.append((stop.latitude, stop.longitude))
            stop_weights.append(stop.weight or 0)
            stop_volumes.append(stop.volume or 0)
            stop_ids.append(stop.id)

        # Add end location if different from origin
        end_location = self._get_destination_location()
        if end_location and end_location.id != origin_location.id:
            locations.append(
                (end_location.partner_latitude, end_location.partner_longitude)
            )
            # End location has no weight/volume
            stop_weights.append(0)
            stop_volumes.append(0)
            stop_ids.append(None)  # Marker for end location

        return locations, stop_weights, stop_volumes, stop_ids

    def _create_day_result(
        self, planning_date, solution, assigned_stops, unassigned_stops
    ):
        """Create a day result record with its routes"""
        day_result = self.env["tms.route.optimizer.day.result"].create(
            {
                "optimizer_id": self.id,
                "planning_date": planning_date,
                "unassigned_stop_ids": [(6, 0, unassigned_stops.ids)]
                if unassigned_stops
                else False,
            }
        )

        # Create result records for this day
        origin_location = self._get_origin_location()
        locations, _, _, stop_ids = self._prepare_location_data_for_stops(
            origin_location, assigned_stops
        )

        vehicles = self._get_vehicles_for_optimization()
        type_mapping = None

        if self.planning_mode == "vehicle_types":
            (
                vehicle_capacities_weight,
                vehicle_capacities_volume,
                _,
                _,
                type_mapping,
            ) = self._prepare_vehicle_data_from_types()
        else:
            vehicle_capacities_weight = None
            vehicle_capacities_volume = None

        for route in solution.get("routes", []):
            vehicle_idx = route["vehicle_id"]
            route_stops = self._get_route_stops_from_ids(
                route, stop_ids, assigned_stops
            )

            if self.planning_mode == "vehicle_types":
                vehicle_type_id = type_mapping[vehicle_idx]
                vehicle = self._get_vehicle_for_type(vehicle_type_id)
                weight_capacity = vehicle_capacities_weight[vehicle_idx]
                volume_capacity = vehicle_capacities_volume[vehicle_idx]
            else:
                vehicle = vehicles[vehicle_idx]
                vehicle_type_id = (
                    vehicle.vehicle_type_id.id if vehicle.vehicle_type_id else False
                )
                weight_capacity = vehicle.weight_capacity
                volume_capacity = vehicle.volume_capacity

            self.env["tms.route.optimizer.result"].create(
                {
                    "optimizer_id": self.id,
                    "day_result_id": day_result.id,
                    "vehicle_id": vehicle.id if vehicle else False,
                    "vehicle_type_id": vehicle_type_id,
                    "stop_ids": [(6, 0, [s.id for s in route_stops])],
                    "stop_count": len(route_stops),
                    "total_distance": route["distance"],
                    "total_weight": route["weight"],
                    "total_volume": route["volume"],
                    "weight_utilization": (
                        (route["weight"] / weight_capacity * 100)
                        if weight_capacity
                        else 0
                    ),
                    "volume_utilization": (
                        (route["volume"] / volume_capacity * 100)
                        if volume_capacity
                        else 0
                    ),
                    "route_cost": route["cost"],
                    "cost_per_km": route["cost"] / route["distance"]
                    if route["distance"] > 0
                    else 0,
                }
            )

        return day_result

    def _get_route_stops_from_ids(self, route, stop_ids, stops):
        """Get stops in route order from a specific stops recordset"""
        route_stops = []
        for node in route["route"][1:-1]:
            stop_idx = node - 1
            if 0 <= stop_idx < len(stop_ids):
                stop_id = stop_ids[stop_idx]
                stop = stops.filtered(lambda s, sid=stop_id: s.id == sid)
                if stop:
                    route_stops.append(stop[0])
        return route_stops

    def _handle_unassignable_stops(self, remaining_stops):
        """Handle stops that couldn't be assigned within planning horizon"""
        # Create a warning message but don't fail
        self.error_message = _(
            "Warning: %(stop_count)d stops could not be assigned within the "
            "%(days)d-day planning horizon. "
            "Consider increasing the horizon or adding more vehicles."
        ) % {"stop_count": len(remaining_stops), "days": self.planning_horizon_days}

    def action_create_orders(self):
        """Create TMS orders from optimization results"""
        if self.state != "done":
            raise UserError(_("Optimization must be completed before creating orders"))

        created_orders = []

        for result in self.result_ids:
            if not result.stop_ids:
                continue

            # Create order first
            # Use start_location_id and end_location_id if available,
            # otherwise fallback to team/company defaults
            origin_location = (
                self.start_location_id
                if self.start_location_id
                else self._get_origin_location()
            )
            destination_location = (
                self.end_location_id
                if self.end_location_id
                else self._get_destination_location()
            )
            order_vals = {
                "name": f"Route {result.vehicle_id.name} - {self.optimization_date}",
                "tms_team_id": self.team_id.id,
                "vehicle_id": result.vehicle_id.id,
                "origin_id": origin_location.id if origin_location else False,
                "destination_id": destination_location.id
                if destination_location
                else False,
            }
            order = self.env["tms.order"].create(order_vals)

            # Create stops in sequence order (One2many relationship)
            # Get stops in the order they appear in result.stop_ids (already sorted)
            for seq, stop in enumerate(result.stop_ids, start=1):
                stop_vals = {
                    "order_id": order.id,
                    "partner_id": stop.partner_id.id,
                    "sequence": seq * 10,  # Use multiples of 10 for easier reordering
                    "weight": stop.weight,
                    "weight_uom_id": stop.weight_uom_id.id
                    if stop.weight_uom_id
                    else False,
                    "volume": stop.volume,
                    "volume_uom_id": stop.volume_uom_id.id
                    if stop.volume_uom_id
                    else False,
                    "unloading_time": stop.unloading_time,
                    "scheduled_date": stop.scheduled_date,
                    "state": "scheduled",
                }
                self.env["tms.order.stop"].create(stop_vals)

            # Update original stop states (if they had an order_id before)
            result.stop_ids.write({"state": "scheduled"})

            # Link result to created order
            result.order_id = order.id

            created_orders.append(order.id)

        # Return action to view created orders
        return {
            "type": "ir.actions.act_window",
            "name": "Created Orders",
            "res_model": "tms.order",
            "view_mode": "list,form",
            "domain": [("id", "in", created_orders)],
        }
