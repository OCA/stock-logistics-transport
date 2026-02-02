from odoo import models


class TMSRouteOptimizer(models.TransientModel):
    _inherit = "tms.route.optimizer"

    def _compute_distance_matrix(self, locations):
        cache = self.env["tms.route.distance.cache"]
        size = len(locations)
        distance_matrix = [[0.0] * size for _ in range(size)]
        for i in range(size):
            lat1, lon1 = locations[i]
            for j in range(i + 1, size):
                lat2, lon2 = locations[j]
                distance = cache.get_distance(lat1, lon1, lat2, lon2)
                distance_matrix[i][j] = distance
                distance_matrix[j][i] = distance
        return distance_matrix
