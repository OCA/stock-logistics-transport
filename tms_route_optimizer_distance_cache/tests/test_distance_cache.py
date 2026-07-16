# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import timedelta

from psycopg2 import IntegrityError

from odoo import fields
from odoo.tests import TransactionCase

SAO_PAULO_COORDS = [
    (-23.6912741, -46.7982916),
    (-23.4387492, -46.729829),
    (-23.4883746, -46.719923),
    (-23.5252592, -46.5491724),
]


class TestDistanceCacheModel(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cache = cls.env["tms.route.distance.cache"]

    def setUp(self):
        super().setUp()
        self.cache.sudo().search([]).unlink()

    def test_normalize_coords_order(self):
        coords = self.cache._normalize_coords(2.0, 2.0, 1.0, 1.0)
        self.assertEqual(coords, (1.0, 1.0, 2.0, 2.0))

    def test_normalize_coords_rounding(self):
        coords = self.cache._normalize_coords(1.12345678, 2.98765432, 3, 4)
        self.assertEqual(coords, (1.123457, 2.987654, 3.0, 4.0))

    def test_normalize_coords_none_values(self):
        self.assertIsNone(self.cache._normalize_coords(None, 2.0, 3.0, 4.0))

    def test_normalize_coords_zero_is_valid(self):
        """Zero is a valid coordinate (equator / prime meridian)."""
        coords = self.cache._normalize_coords(0.0, 2.0, 3.0, 4.0)
        self.assertIsNotNone(coords)
        self.assertEqual(coords, (0.0, 2.0, 3.0, 4.0))

    def test_get_distance_returns_none_on_miss(self):
        """get_distance returns None when the pair is not cached."""
        result = self.cache.get_distance(1.0, 1.0, 2.0, 2.0)
        self.assertIsNone(result)

    def test_store_distance_creates_cache(self):
        """store_distance creates a cache entry."""
        self.cache.store_distance(1.0, 1.0, 2.0, 2.0, 157.0, "haversine")
        self.assertEqual(self.cache.sudo().search_count([]), 1)

    def test_get_distance_returns_cached(self):
        """get_distance returns the stored value after store_distance."""
        self.cache.store_distance(1.0, 1.0, 2.0, 2.0, 157.0, "haversine")
        result = self.cache.get_distance(1.0, 1.0, 2.0, 2.0)
        self.assertEqual(result, 157.0)

    def test_get_distance_updates_last_used(self):
        self.cache.store_distance(1.0, 1.0, 2.0, 2.0, 157.0)
        record = self.cache.sudo().search([], limit=1)
        old_time = fields.Datetime.now() - timedelta(days=1)
        record.write({"last_used": old_time})
        self.cache.get_distance(1.0, 1.0, 2.0, 2.0)
        record.invalidate_recordset()
        self.assertGreater(record.last_used, old_time)

    def test_get_distance_symmetry(self):
        self.cache.store_distance(1.0, 1.0, 2.0, 2.0, 157.0)
        result = self.cache.get_distance(2.0, 2.0, 1.0, 1.0)
        self.assertEqual(result, 157.0)
        self.assertEqual(self.cache.sudo().search_count([]), 1)

    def test_cache_unique_constraint(self):
        self.cache.sudo().create(
            {
                "lat_a": 1.0,
                "lon_a": 1.0,
                "lat_b": 2.0,
                "lon_b": 2.0,
                "distance_km": 10.0,
                "last_used": fields.Datetime.now(),
            }
        )
        with self.assertRaises(IntegrityError):
            self.cache.sudo().create(
                {
                    "lat_a": 1.0,
                    "lon_a": 1.0,
                    "lat_b": 2.0,
                    "lon_b": 2.0,
                    "distance_km": 10.0,
                    "last_used": fields.Datetime.now(),
                }
            )

    def test_store_distance_provider_field(self):
        """store_distance records the provider name."""
        self.cache.store_distance(1.0, 1.0, 2.0, 2.0, 157.0, "osrm")
        record = self.cache.sudo().search([], limit=1)
        self.assertEqual(record.distance_provider, "osrm")

    def test_store_distance_duplicate_is_safe(self):
        """Storing the same pair twice should not raise an error."""
        self.cache.store_distance(1.0, 1.0, 2.0, 2.0, 157.0, "haversine")
        # Second store with same coords must not crash (IntegrityError handled)
        self.cache.store_distance(1.0, 1.0, 2.0, 2.0, 160.0, "osrm")
        # Original value is kept (first writer wins)
        self.assertEqual(self.cache.sudo().search_count([]), 1)
        record = self.cache.sudo().search([], limit=1)
        self.assertEqual(record.distance_km, 157.0)

    def test_cleanup_lru_removes_oldest(self):
        self.cache.sudo().create(
            {
                "lat_a": 1.0,
                "lon_a": 1.0,
                "lat_b": 1.5,
                "lon_b": 1.5,
                "distance_km": 5.0,
                "last_used": fields.Datetime.now() - timedelta(days=1),
            }
        )
        self.cache.sudo().create(
            {
                "lat_a": 2.0,
                "lon_a": 2.0,
                "lat_b": 2.5,
                "lon_b": 2.5,
                "distance_km": 5.0,
                "last_used": fields.Datetime.now(),
            }
        )
        self.cache.sudo().create(
            {
                "lat_a": 3.0,
                "lon_a": 3.0,
                "lat_b": 3.5,
                "lon_b": 3.5,
                "distance_km": 5.0,
                "last_used": fields.Datetime.now(),
            }
        )
        self.cache.cleanup_lru(limit=2)
        self.assertEqual(self.cache.sudo().search_count([]), 2)

    def test_cleanup_lru_respects_limit(self):
        self.cache.store_distance(1.0, 1.0, 2.0, 2.0, 10.0)
        self.cache.store_distance(3.0, 3.0, 4.0, 4.0, 20.0)
        self.cache.cleanup_lru(limit=3)
        self.assertEqual(self.cache.sudo().search_count([]), 2)

    def test_cleanup_lru_zero_limit(self):
        self.cache.store_distance(1.0, 1.0, 2.0, 2.0, 10.0)
        self.cache.store_distance(3.0, 3.0, 4.0, 4.0, 20.0)
        self.cache.cleanup_lru(limit=0)
        self.assertEqual(self.cache.sudo().search_count([]), 2)

    def test_cron_cleanup_method(self):
        self.cache.store_distance(1.0, 1.0, 2.0, 2.0, 10.0)
        self.cache.store_distance(3.0, 3.0, 4.0, 4.0, 20.0)
        self.env["ir.config_parameter"].sudo().set_param(
            "tms.route_optimizer.distance_cache_limit", "1"
        )
        self.cache.cron_cleanup_distance_cache()
        self.assertLessEqual(self.cache.sudo().search_count([]), 1)


class TestDistanceCacheIntegration(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cache = cls.env["tms.route.distance.cache"]
        cls.team = cls.env["tms.team"].create({"name": "Cache Team"})

    def setUp(self):
        super().setUp()
        self.cache.sudo().search([]).unlink()

    def _new_wizard(self):
        return self.env["tms.route.optimizer"].new({})

    def test_compute_distance_matrix_uses_cache(self):
        wizard = self._new_wizard()
        matrix = wizard._compute_distance_matrix(SAO_PAULO_COORDS)
        self.assertEqual(len(matrix), len(SAO_PAULO_COORDS))
        expected_pairs = 6  # 4 pontos -> 4*3/2
        self.assertEqual(self.cache.sudo().search_count([]), expected_pairs)

    def test_compute_distance_matrix_reuses_cache(self):
        wizard = self._new_wizard()
        wizard._compute_distance_matrix(SAO_PAULO_COORDS)
        count_before = self.cache.sudo().search_count([])
        wizard._compute_distance_matrix(SAO_PAULO_COORDS)
        count_after = self.cache.sudo().search_count([])
        self.assertEqual(count_before, count_after)

    def test_compute_distance_matrix_symmetry(self):
        wizard = self._new_wizard()
        matrix = wizard._compute_distance_matrix(SAO_PAULO_COORDS)
        for i in range(len(SAO_PAULO_COORDS)):
            for j in range(len(SAO_PAULO_COORDS)):
                self.assertAlmostEqual(matrix[i][j], matrix[j][i], places=10)

    def test_optimization_with_cache(self):
        try:
            import ortools.constraint_solver  # noqa: F401
        except ImportError:
            self.skipTest("ortools not installed; integration test skipped")

        wizard = self.env["tms.route.optimizer"].create(
            {
                "team_id": self.team.id,
                "planning_mode": "team",
                "date_from": fields.Datetime.now(),
                "date_to": fields.Datetime.now(),
                "optimization_date": fields.Date.today(),
            }
        )
        locations = SAO_PAULO_COORDS
        solution = wizard._solve_vrp(
            locations,
            stop_weights=[1.0] * (len(locations) - 1),
            stop_volumes=[1.0] * (len(locations) - 1),
            vehicle_capacities_weight=[10.0],
            vehicle_capacities_volume=[10.0],
            cost_per_km=[1.0],
            minimum_trip_cost=[0.0],
        )
        self.assertIsNotNone(solution)
        self.assertGreaterEqual(self.cache.sudo().search_count([]), 6)
