# TMS Route Optimizer

This module provides route optimization functionality for TMS (Transport Management
System) using Google OR-Tools. It solves Vehicle Routing Problems (VRP) to find optimal
routes for multiple delivery stops, considering vehicle capacity constraints, distances,
and costs.

## Key Features

- **Route Optimization**: Uses Google OR-Tools to solve VRP problems
- **Multi-Vehicle Support**: Distributes stops across multiple vehicles
- **Capacity Constraints**: Considers weight and volume capacity of vehicles
- **Distance Calculation**: Uses Haversine formula to calculate distances between
  locations
- **Cost Optimization**: Minimizes total cost considering distance and vehicle costs
- **Automatic Order Creation**: Creates TMS orders from optimized routes
- **Visualization**: Provides Google Maps and Waze URLs for each route
- **Performance Metrics**: Shows utilization rates, distances, and costs per route

## Use Cases

- Optimize delivery routes for multiple stops
- Minimize transportation costs
- Maximize vehicle capacity utilization
- Plan efficient multi-vehicle delivery operations
- Reduce total distance traveled
- Improve delivery time estimation

## Technical Details

- **Algorithm**: Vehicle Routing Problem (VRP) solver using Google OR-Tools
- **Distance Calculation**: Haversine formula for great-circle distances
- **Constraints**: Weight capacity, volume capacity, vehicle availability
- **Objective**: Minimize total cost (distance × cost per km + minimum trip cost)
