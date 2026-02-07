from odoo import api, fields, models


class TMSRouteDistanceCache(models.Model):
    _name = "tms.route.distance.cache"
    _description = "TMS Route Distance Cache"
    _order = "last_used desc"

    lat_a = fields.Float(required=True)
    lon_a = fields.Float(required=True)
    lat_b = fields.Float(required=True)
    lon_b = fields.Float(required=True)
    distance_km = fields.Float(required=True)
    distance_provider = fields.Char(
        help="Provider that computed this distance (e.g. haversine, osrm).",
    )
    last_used = fields.Datetime(required=True, default=fields.Datetime.now)

    _sql_constraints = [
        (
            "route_distance_cache_unique",
            "unique(lat_a, lon_a, lat_b, lon_b)",
            "Distance cache entry already exists.",
        )
    ]

    @api.model
    def _normalize_coords(self, lat1, lon1, lat2, lon2):
        if any(v is None for v in (lat1, lon1, lat2, lon2)):
            return None
        if not all([lat1, lon1, lat2, lon2]):
            return None
        point_a = (round(lat1, 6), round(lon1, 6))
        point_b = (round(lat2, 6), round(lon2, 6))
        if point_b < point_a:
            point_a, point_b = point_b, point_a
        return point_a[0], point_a[1], point_b[0], point_b[1]

    @api.model
    def _get_cache_limit(self):
        param = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("tms.route_optimizer.distance_cache_limit", "200000")
        )
        try:
            return int(param)
        except (TypeError, ValueError):
            return 0

    @api.model
    def cleanup_lru(self, limit):
        if not limit or limit <= 0:
            return
        count = self.sudo().search_count([])
        if count <= limit:
            return
        to_remove = count - limit
        old_records = self.sudo().search([], order="last_used asc", limit=to_remove)
        if old_records:
            old_records.unlink()

    @api.model
    def get_distance(self, lat1, lon1, lat2, lon2):
        coords = self._normalize_coords(lat1, lon1, lat2, lon2)
        if not coords:
            return 0.0

        lat_a, lon_a, lat_b, lon_b = coords
        cache = self.sudo().search(
            [
                ("lat_a", "=", lat_a),
                ("lon_a", "=", lon_a),
                ("lat_b", "=", lat_b),
                ("lon_b", "=", lon_b),
            ],
            limit=1,
        )
        now = fields.Datetime.now()
        if cache:
            cache.write({"last_used": now})
            return cache.distance_km

        return None

    @api.model
    def store_distance(self, lat1, lon1, lat2, lon2, distance, provider=""):
        """Store a computed distance in the cache."""
        coords = self._normalize_coords(lat1, lon1, lat2, lon2)
        if not coords:
            return
        lat_a, lon_a, lat_b, lon_b = coords
        self.sudo().create(
            {
                "lat_a": lat_a,
                "lon_a": lon_a,
                "lat_b": lat_b,
                "lon_b": lon_b,
                "distance_km": distance,
                "distance_provider": provider,
                "last_used": fields.Datetime.now(),
            }
        )
        self.cleanup_lru(self._get_cache_limit())

    @api.model
    def cron_cleanup_distance_cache(self):
        self.cleanup_lru(self._get_cache_limit())
