This module provides OSRM (Open Source Routing Machine) integration for
the TMS Route Optimizer, enabling real road-based distance calculations.

Features:

- OSRM distance matrix API integration (Table endpoint)
- Route geometry retrieval for polylines (Route endpoint)
- Automatic fallback to Haversine if OSRM unavailable
- Configurable OSRM server URL (public or self-hosted)
- More accurate ETA calculation based on actual road distances

By installing this module, the route optimizer will automatically use
OSRM for distance calculations instead of straight-line Haversine,
resulting in more accurate route optimization.
