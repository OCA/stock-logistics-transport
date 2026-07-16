# TMS Route Optimizer Distance Cache

This module extends the TMS Route Optimizer by adding a persistent distance cache to
significantly improve performance when optimizing routes with overlapping locations.

## Key Features

- **Persistent Distance Cache**: Stores calculated distances between coordinate pairs in the
  database
- **Automatic Cache Management**: Uses LRU (Least Recently Used) strategy to limit cache size
- **Performance Boost**: Eliminates redundant distance calculations across optimizations
- **Coordinate Normalization**: Ensures consistent cache lookups through coordinate rounding
  and ordering
- **Scheduled Cleanup**: Automatic daily cleanup to maintain cache size limits
- **Seamless Integration**: Transparent caching with no changes to existing optimization
  workflows

## Use Cases

- **Multiple Daily Optimizations**: Reuse distance calculations when optimizing similar
  routes throughout the day
- **Recurring Deliveries**: Speed up optimizations for frequently visited locations
- **Large-Scale Operations**: Reduce computation time for routes with many overlapping stops
- **Performance Optimization**: Minimize API calls and calculation overhead

## Technical Details

- **Cache Model**: `tms.route.distance.cache` stores coordinate pairs and distances
- **LRU Strategy**: Automatically removes oldest unused entries when limit is reached
- **Configurable Limit**: Default 200,000 entries (configurable via system parameter)
- **Coordinate Precision**: 6 decimal places (~0.1 meter accuracy)
- **Automatic Updates**: Last used timestamp updated on each cache hit
- **Scheduled Cleanup**: Daily cron job to enforce cache size limits
