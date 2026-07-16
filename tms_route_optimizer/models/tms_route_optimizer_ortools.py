import math

try:
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2
except ImportError:
    pywrapcp = None
    routing_enums_pb2 = None


class RouteOptimizerHelper:
    """
    Helper class for OR-Tools route optimization.

    Provides static methods for:
    - Calculating distances between geographic coordinates (Haversine)
    - Generating distance matrices for multiple locations
    - Solving Vehicle Routing Problems (VRP) with capacity constraints
    - Generating Google Maps navigation URLs
    """

    @staticmethod
    def haversine_distance(lat1, lon1, lat2, lon2):
        """
        Calculate distance between two coordinates using Haversine formula.

        Args:
            lat1: Latitude of first point
            lon1: Longitude of first point
            lat2: Latitude of second point
            lon2: Longitude of second point

        Returns:
            Distance in kilometers (0.0 if any coordinate is missing)
        """
        if not all([lat1, lon1, lat2, lon2]):
            return 0.0

        R = 6371  # Earth's radius in kilometers
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))

        return R * c

    @staticmethod
    def calculate_distance_matrix(locations):
        """
        Calculate distance matrix between all locations using Haversine formula.

        Args:
            locations: List of (latitude, longitude) tuples

        Returns:
            2D list of distances in km (symmetric matrix with zeros on diagonal)
        """
        n = len(locations)
        distance_matrix = [[0.0] * n for _ in range(n)]

        for i in range(n):
            for j in range(n):
                if i != j:
                    lat1, lon1 = locations[i]
                    lat2, lon2 = locations[j]
                    distance_matrix[i][j] = RouteOptimizerHelper.haversine_distance(
                        lat1, lon1, lat2, lon2
                    )

        return distance_matrix

    @staticmethod
    def _extract_solution(
        solution,
        routing,
        manager,
        num_vehicles,
        distance_matrix,
        stop_weights,
        stop_volumes,
        cost_per_km,
        minimum_trip_cost,
        allow_partial_routes,
        num_stops,
        end_depot=None,
    ):
        """Extract solution routes from OR-Tools routing solution."""
        routes = []
        total_distance = 0
        total_cost = 0
        start_depot = 0

        for vehicle_id in range(num_vehicles):
            index = routing.Start(vehicle_id)
            route = []
            route_distance = 0
            route_weight = 0
            route_volume = 0

            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                route.append(node_index)

                # Only count weight/volume for actual stops (not depots)
                if node_index > 0 and node_index <= num_stops:
                    route_weight += stop_weights[node_index - 1]
                    route_volume += stop_volumes[node_index - 1]

                previous_index = index
                index = solution.Value(routing.NextVar(index))

                # Calculate distance between nodes
                if node_index > 0 or not routing.IsEnd(index):
                    route_distance += distance_matrix[
                        manager.IndexToNode(previous_index)
                    ][manager.IndexToNode(index)]

            # Add end depot node
            end_node = manager.IndexToNode(index)
            route.append(end_node)

            if len(route) > 2:  # Only add routes with actual stops
                route_cost = minimum_trip_cost[vehicle_id] + (
                    route_distance * cost_per_km[vehicle_id]
                )
                routes.append(
                    {
                        "vehicle_id": vehicle_id,
                        "route": route,
                        "distance": route_distance,
                        "cost": route_cost,
                        "weight": route_weight,
                        "volume": route_volume,
                    }
                )
                total_distance += route_distance
                total_cost += route_cost

        result = {
            "routes": routes,
            "total_distance": total_distance,
            "total_cost": total_cost,
            "num_vehicles_used": len([r for r in routes if len(r["route"]) > 2]),
        }

        # Calculate unvisited nodes if partial routes are allowed
        if allow_partial_routes:
            visited_nodes = set()
            for route in routes:
                visited_nodes.update(route["route"])
            # Remove depots from consideration
            visited_nodes.discard(start_depot)
            if end_depot is not None:
                visited_nodes.discard(end_depot)
            all_nodes = set(range(1, num_stops + 1))
            unvisited_nodes = list(all_nodes - visited_nodes)
            result["unvisited_nodes"] = unvisited_nodes

        return result

    @staticmethod
    def _create_routing_manager(num_stops, num_vehicles, start_depot, end_depot):
        """Create routing index manager with appropriate depot configuration."""
        if end_depot is not None and end_depot != start_depot:
            return pywrapcp.RoutingIndexManager(
                num_stops + 1, num_vehicles, start_depot, end_depot
            )
        return pywrapcp.RoutingIndexManager(num_stops + 1, num_vehicles, start_depot)

    @staticmethod
    def _add_weight_dimension(
        routing,
        manager,
        stop_weights,
        vehicle_capacities_weight,
        start_depot,
        end_depot,
        num_stops,
    ):
        """Add weight capacity dimension to routing model."""

        def weight_callback(from_index):
            from_node = manager.IndexToNode(from_index)
            if from_node == start_depot or (
                end_depot is not None and from_node == end_depot
            ):
                return 0
            if from_node > 0 and from_node <= num_stops:
                return int(stop_weights[from_node - 1] * 1000)
            return 0

        weight_callback_index = routing.RegisterUnaryTransitCallback(weight_callback)
        weight_capacities = [int(cap * 1000) for cap in vehicle_capacities_weight]
        routing.AddDimensionWithVehicleCapacity(
            weight_callback_index, 0, weight_capacities, True, "Weight"
        )

    @staticmethod
    def _add_volume_dimension(
        routing,
        manager,
        stop_volumes,
        vehicle_capacities_volume,
        start_depot,
        end_depot,
        num_stops,
    ):
        """Add volume capacity dimension to routing model."""

        def volume_callback(from_index):
            from_node = manager.IndexToNode(from_index)
            if from_node == start_depot or (
                end_depot is not None and from_node == end_depot
            ):
                return 0
            if from_node > 0 and from_node <= num_stops:
                return int(stop_volumes[from_node - 1] * 1000)
            return 0

        volume_callback_index = routing.RegisterUnaryTransitCallback(volume_callback)
        volume_capacities = [int(cap * 1000) for cap in vehicle_capacities_volume]
        routing.AddDimensionWithVehicleCapacity(
            volume_callback_index, 0, volume_capacities, True, "Volume"
        )

    @staticmethod
    def _add_stop_count_dimension(
        routing, manager, max_stops_per_vehicle, num_vehicles, start_depot, end_depot
    ):
        """Add stop count dimension to routing model."""

        def stop_count_callback(from_index):
            from_node = manager.IndexToNode(from_index)
            if from_node == start_depot or (
                end_depot is not None and from_node == end_depot
            ):
                return 0
            return 1

        count_callback_index = routing.RegisterUnaryTransitCallback(stop_count_callback)
        routing.AddDimensionWithVehicleCapacity(
            count_callback_index,
            0,
            [max_stops_per_vehicle] * num_vehicles,
            True,
            "StopCount",
        )

    @staticmethod
    def _configure_partial_routes(
        routing, manager, distance_matrix, cost_per_km, num_stops
    ):
        """Configure disjunctions to allow partial routes."""
        max_distance = (
            max(max(row) for row in distance_matrix) if distance_matrix else 100
        )
        max_cost_per_km = max(cost_per_km) if cost_per_km else 5.0
        drop_penalty = int(max_distance * max_cost_per_km * num_stops * 10 * 1000)

        for node in range(1, num_stops + 1):
            routing.AddDisjunction([manager.NodeToIndex(node)], drop_penalty)

    @staticmethod
    def _configure_search_parameters(
        max_time_seconds,
        first_solution_strategy,
        local_search_metaheuristic,
        solution_limit,
    ):
        """Configure search parameters for the routing solver."""
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()

        if first_solution_strategy:
            search_parameters.first_solution_strategy = getattr(
                routing_enums_pb2.FirstSolutionStrategy, first_solution_strategy
            )
        else:
            search_parameters.first_solution_strategy = (
                routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
            )

        if local_search_metaheuristic:
            search_parameters.local_search_metaheuristic = getattr(
                routing_enums_pb2.LocalSearchMetaheuristic, local_search_metaheuristic
            )
        else:
            search_parameters.local_search_metaheuristic = (
                routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
            )

        search_parameters.time_limit.seconds = int(max_time_seconds)
        if solution_limit and int(solution_limit) > 0:
            search_parameters.solution_limit = int(solution_limit)

        return search_parameters

    @staticmethod
    def solve_vrp(
        distance_matrix,
        vehicle_capacities_weight,
        vehicle_capacities_volume,
        stop_weights,
        stop_volumes,
        cost_per_km,
        minimum_trip_cost,
        max_time_seconds=300,
        max_stops_per_vehicle=0,
        allow_partial_routes=False,
        end_depot=None,
        first_solution_strategy=None,
        local_search_metaheuristic=None,
        solution_limit=0,
    ):
        """
        Solve Vehicle Routing Problem using OR-Tools.

        Args:
            distance_matrix: 2D list of distances in km between locations
            vehicle_capacities_weight: List of weight capacities per vehicle (kg)
            vehicle_capacities_volume: List of volume capacities per vehicle (m³)
            stop_weights: List of weights for each stop (kg)
            stop_volumes: List of volumes for each stop (m³)
            cost_per_km: List of costs per km for each vehicle
            minimum_trip_cost: List of minimum trip costs per vehicle
            max_time_seconds: Maximum time for optimization (default: 300)
            max_stops_per_vehicle: Maximum stops per vehicle, 0 means no limit
            allow_partial_routes: If True, allow some stops to remain unvisited
                when capacity is insufficient (for multi-day planning)
            end_depot: Optional index of end depot (if different from start depot).
                If None, routes return to start depot.

        Returns:
            dict with solution data containing:
            - routes: List of route dictionaries with vehicle_id, route, distance,
              cost, weight, volume
            - total_distance: Total distance of all routes (km)
            - total_cost: Total cost of all routes
            - num_vehicles_used: Number of vehicles with actual stops
            - unvisited_nodes: List of node indices that were not visited
              (only when allow_partial_routes=True)
            None if no solution found
        """
        if not pywrapcp:
            raise ImportError("ortools is not installed")

        num_stops = len(stop_weights)
        num_vehicles = len(vehicle_capacities_weight)
        start_depot = 0

        # Create routing manager and model
        manager = RouteOptimizerHelper._create_routing_manager(
            num_stops, num_vehicles, start_depot, end_depot
        )
        routing = pywrapcp.RoutingModel(manager)

        # Create distance callback
        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return int(distance_matrix[from_node][to_node] * 1000)

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        # Add capacity dimensions
        RouteOptimizerHelper._add_weight_dimension(
            routing,
            manager,
            stop_weights,
            vehicle_capacities_weight,
            start_depot,
            end_depot,
            num_stops,
        )
        RouteOptimizerHelper._add_volume_dimension(
            routing,
            manager,
            stop_volumes,
            vehicle_capacities_volume,
            start_depot,
            end_depot,
            num_stops,
        )

        # Add stop count dimension if needed
        if max_stops_per_vehicle > 0:
            RouteOptimizerHelper._add_stop_count_dimension(
                routing,
                manager,
                max_stops_per_vehicle,
                num_vehicles,
                start_depot,
                end_depot,
            )

        # Configure partial routes if needed
        if allow_partial_routes:
            RouteOptimizerHelper._configure_partial_routes(
                routing, manager, distance_matrix, cost_per_km, num_stops
            )

        # Set search parameters
        search_parameters = RouteOptimizerHelper._configure_search_parameters(
            max_time_seconds,
            first_solution_strategy,
            local_search_metaheuristic,
            solution_limit,
        )

        # Solve
        solution = routing.SolveWithParameters(search_parameters)

        if not solution:
            return None

        # Extract solution
        return RouteOptimizerHelper._extract_solution(
            solution,
            routing,
            manager,
            num_vehicles,
            distance_matrix,
            stop_weights,
            stop_volumes,
            cost_per_km,
            minimum_trip_cost,
            allow_partial_routes,
            num_stops,
            end_depot,
        )

    @staticmethod
    def generate_google_maps_url(coordinates):
        """
        Generate Google Maps URL for a route with waypoints.

        Args:
            coordinates: List of (latitude, longitude) tuples

        Returns:
            Google Maps URL string or None if insufficient coordinates
        """
        if not coordinates or len(coordinates) < 2:
            return None

        origin = f"{coordinates[0][0]},{coordinates[0][1]}"
        destination = f"{coordinates[-1][0]},{coordinates[-1][1]}"

        waypoints = []
        for lat, lon in coordinates[1:-1]:
            waypoints.append(f"{lat},{lon}")

        waypoints_str = "|".join(waypoints) if waypoints else ""

        url = (
            f"https://www.google.com/maps/dir/?api=1"
            f"&origin={origin}&destination={destination}"
        )
        if waypoints_str:
            url += f"&waypoints={waypoints_str}"

        return url
