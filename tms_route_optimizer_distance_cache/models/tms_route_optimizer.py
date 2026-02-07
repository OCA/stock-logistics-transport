import logging

from odoo import models

_logger = logging.getLogger(__name__)


class TMSRouteOptimizer(models.TransientModel):
    _inherit = "tms.route.optimizer"

    def _compute_distance_matrix(self, locations):
        """
        Override to add caching layer around the distance computation.

        Strategy:
        1. Check cache for each pair of locations
        2. For cache misses, delegate to super() (which may be OSRM or Haversine)
        3. Store computed distances in cache
        """
        cache_model = self.env["tms.route.distance.cache"]
        size = len(locations)
        distance_matrix = [[0.0] * size for _ in range(size)]
        miss_pairs = []

        # Phase 1: Check cache for all pairs
        for i in range(size):
            lat1, lon1 = locations[i]
            for j in range(i + 1, size):
                lat2, lon2 = locations[j]
                cached = cache_model.get_distance(lat1, lon1, lat2, lon2)
                if cached is not None:
                    distance_matrix[i][j] = cached
                    distance_matrix[j][i] = cached
                else:
                    miss_pairs.append((i, j))

        if not miss_pairs:
            _logger.info(
                "Distance cache: all %d pairs found in cache", size * (size - 1) // 2
            )
            return distance_matrix

        # Phase 2: Compute full matrix from super() for misses
        _logger.info(
            "Distance cache: %d hits, %d misses",
            size * (size - 1) // 2 - len(miss_pairs),
            len(miss_pairs),
        )
        computed_matrix = super()._compute_distance_matrix(locations)

        # Phase 3: Fill misses from computed matrix and store in cache
        for i, j in miss_pairs:
            distance = computed_matrix[i][j]
            distance_matrix[i][j] = distance
            distance_matrix[j][i] = distance

            lat1, lon1 = locations[i]
            lat2, lon2 = locations[j]
            cache_model.store_distance(lat1, lon1, lat2, lon2, distance)

        return distance_matrix
