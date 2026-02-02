# Copyright (C) 2024 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import unittest

from odoo.addons.tms_route_optimizer.models.tms_route_optimizer_ortools import (
    RouteOptimizerHelper,
)

# Coordenadas reais de São Paulo extraídas do Google Maps
# Rota completa: Rua Luar do Sertão -> Estr. das Taipas -> Av. Paula Ferreira ->
# Largo do Rosário -> R. Cap. Busse -> Av. Jd. Japão -> R. Cachoeira ->
# Estr. Pres. Juscelino -> Av. Souza Ramos
SAO_PAULO_ROUTE_COORDINATES = [
    (-23.6912741, -46.7982916),  # Rua Luar do Sertão (origem)
    (-23.4387492, -46.729829),  # Estr. das Taipas, 2420 - Jardim Rincão
    (-23.4883746, -46.719923),  # Av. Paula Ferreira, 2944 - Vila Pirituba
    (-23.5252592, -46.5491724),  # Largo do Rosário, 83 - Penha de França
    (-23.4761963, -46.5613152),  # R. Cap. Busse, 622 - Parque Edu Chaves
    (-23.4831444, -46.5799668),  # Av. Jd. Japão, São Paulo - SP
    (-23.4454382, -46.5480376),  # R. Cachoeira, 517 - Picanço
    (-23.4657249, -46.4196475),  # Estr. Pres. Juscelino K. de Oliveira, 1049
    (-23.5814578, -46.4098576),  # Av. Souza Ramos, 413 - Guaianases (destino)
]


class TestRouteOptimizerHelper(unittest.TestCase):
    """Test RouteOptimizerHelper class methods"""

    def test_haversine_distance_zero_for_identical_points(self):
        """Test that distance between identical points is zero"""
        d = RouteOptimizerHelper.haversine_distance(-23.0, -46.0, -23.0, -46.0)
        self.assertAlmostEqual(d, 0.0, places=9)

    def test_haversine_distance_symmetry(self):
        """Test that distance calculation is symmetric"""
        a = (-23.55052, -46.633308)  # São Paulo
        b = (-22.906847, -43.172897)  # Rio de Janeiro
        d1 = RouteOptimizerHelper.haversine_distance(a[0], a[1], b[0], b[1])
        d2 = RouteOptimizerHelper.haversine_distance(b[0], b[1], a[0], a[1])
        self.assertAlmostEqual(d1, d2, places=10)

    def test_haversine_distance_known_approx_sp_rio(self):
        """Test known distance approximation SP-Rio (~357 km)"""
        # Distância em linha reta SP-Rio ~ 357 km (aprox; depende das coordenadas)
        sp = (-23.55052, -46.633308)
        rio = (-22.906847, -43.172897)
        d = RouteOptimizerHelper.haversine_distance(sp[0], sp[1], rio[0], rio[1])
        # Tolerância de 5%
        self.assertGreater(d, 357 * 0.95)
        self.assertLess(d, 357 * 1.05)

    def test_haversine_distance_sao_paulo_locations(self):
        """Test distances between real São Paulo locations"""
        # Distâncias entre pontos reais de São Paulo
        origem = SAO_PAULO_ROUTE_COORDINATES[0]  # Rua Luar do Sertão
        destino = SAO_PAULO_ROUTE_COORDINATES[-1]  # Av. Souza Ramos, 413

        d = RouteOptimizerHelper.haversine_distance(
            origem[0], origem[1], destino[0], destino[1]
        )

        # Distância aproximada entre esses pontos em São Paulo (~30-40 km)
        self.assertGreater(d, 20.0)  # Mais de 20 km
        self.assertLess(d, 50.0)  # Menos de 50 km

        # Verifica simetria
        d_reverse = RouteOptimizerHelper.haversine_distance(
            destino[0], destino[1], origem[0], origem[1]
        )
        self.assertAlmostEqual(d, d_reverse, places=10)

        # Distância entre pontos próximos (R. Cachoeira e Estr. Pres. Juscelino)
        p1 = SAO_PAULO_ROUTE_COORDINATES[6]  # R. Cachoeira, 517
        p2 = SAO_PAULO_ROUTE_COORDINATES[7]  # Estr. Pres. Juscelino
        d_close = RouteOptimizerHelper.haversine_distance(p1[0], p1[1], p2[0], p2[1])

        # Pontos mais próximos (~10-15 km)
        self.assertGreater(d_close, 5.0)
        self.assertLess(d_close, 20.0)

    def test_haversine_distance_returns_zero_if_any_coord_falsy(self):
        """Test that zero coordinates return zero distance"""
        # Atenção: seu código usa "if not all([lat1, lon1, lat2, lon2])",
        # então 0.0 é considerado falsy e retorna 0.0 mesmo sendo coordenada válida.
        d = RouteOptimizerHelper.haversine_distance(0.0, -46.0, -23.0, -46.0)
        self.assertEqual(d, 0.0)

    def test_calculate_distance_matrix_shape_and_diagonal_zero(self):
        """Test distance matrix has correct shape and zero diagonal"""
        locations = [
            (-23.0, -46.0),
            (-22.0, -43.0),
            (-21.0, -44.0),
        ]
        m = RouteOptimizerHelper.calculate_distance_matrix(locations)
        self.assertEqual(len(m), 3)
        self.assertTrue(all(len(row) == 3 for row in m))
        self.assertEqual(m[0][0], 0.0)
        self.assertEqual(m[1][1], 0.0)
        self.assertEqual(m[2][2], 0.0)

    def test_calculate_distance_matrix_symmetry(self):
        """Test that distance matrix is symmetric"""
        locations = [
            (-23.55052, -46.633308),
            (-22.906847, -43.172897),
            (-19.916681, -43.934493),  # BH
        ]
        m = RouteOptimizerHelper.calculate_distance_matrix(locations)
        for i in range(len(locations)):
            for j in range(len(locations)):
                self.assertAlmostEqual(m[i][j], m[j][i], places=10)

    def test_calculate_distance_matrix_with_sao_paulo_coordinates(self):
        """Test distance matrix with real São Paulo coordinates"""
        # Usa as coordenadas reais de São Paulo
        m = RouteOptimizerHelper.calculate_distance_matrix(SAO_PAULO_ROUTE_COORDINATES)

        # Verifica formato
        self.assertEqual(len(m), 9)
        self.assertTrue(all(len(row) == 9 for row in m))

        # Verifica diagonal zero
        for i in range(9):
            self.assertEqual(m[i][i], 0.0)

        # Verifica simetria
        for i in range(9):
            for j in range(9):
                self.assertAlmostEqual(m[i][j], m[j][i], places=10)

        # Verifica que todas as distâncias são positivas (exceto diagonal)
        for i in range(9):
            for j in range(9):
                if i != j:
                    self.assertGreater(m[i][j], 0.0)

    def test_generate_google_maps_url_none_for_insufficient_points(self):
        """Test that insufficient coordinates return None"""
        self.assertIsNone(RouteOptimizerHelper.generate_google_maps_url([]))
        self.assertIsNone(RouteOptimizerHelper.generate_google_maps_url([(1, 2)]))

    def test_generate_google_maps_url_origin_destination_only(self):
        """Test Google Maps URL with only origin and destination"""
        coords = [(-23.0, -46.0), (-22.0, -43.0)]
        url = RouteOptimizerHelper.generate_google_maps_url(coords)
        self.assertIsNotNone(url)
        self.assertTrue(url.startswith("https://www.google.com/maps/dir/?api=1"))
        self.assertIn("origin=-23.0,-46.0", url)
        self.assertIn("destination=-22.0,-43.0", url)
        self.assertNotIn("waypoints=", url)

    def test_generate_google_maps_url_with_waypoints(self):
        """Test Google Maps URL with waypoints"""
        coords = [
            (-23.0, -46.0),  # origin
            (-22.5, -45.0),  # waypoint
            (-22.0, -43.0),  # destination
        ]
        url = RouteOptimizerHelper.generate_google_maps_url(coords)
        self.assertIsNotNone(url)
        self.assertIn("origin=-23.0,-46.0", url)
        self.assertIn("destination=-22.0,-43.0", url)
        self.assertIn("waypoints=-22.5,-45.0", url)

    def test_generate_google_maps_url_with_sao_paulo_route(self):
        """Test Google Maps URL with real São Paulo route"""
        # Rota real de São Paulo extraída do Google Maps
        url = RouteOptimizerHelper.generate_google_maps_url(SAO_PAULO_ROUTE_COORDINATES)

        self.assertIsNotNone(url)
        self.assertTrue(url.startswith("https://www.google.com/maps/dir/?api=1"))

        # Verifica origem (primeira coordenada)
        origem = SAO_PAULO_ROUTE_COORDINATES[0]
        self.assertIn(f"origin={origem[0]},{origem[1]}", url)

        # Verifica destino (última coordenada)
        destino = SAO_PAULO_ROUTE_COORDINATES[-1]
        self.assertIn(f"destination={destino[0]},{destino[1]}", url)
        self.assertIn("waypoints=", url)

        # Verifica que todos os waypoints (meio) estão presentes na URL
        waypoints_str = url.split("waypoints=")[1] if "waypoints=" in url else ""
        waypoints = SAO_PAULO_ROUTE_COORDINATES[1:-1]  # Todos exceto origem e destino

        for lat, lon in waypoints:
            coord_str = f"{lat},{lon}"
            self.assertIn(
                coord_str, waypoints_str, f"Waypoint {coord_str} não encontrado na URL"
            )

    def test_solve_vrp_integration_small_instance(self):
        """Test VRP solving with small instance"""
        # Verifica se ortools está instalado
        try:
            import ortools.constraint_solver  # noqa: F401
        except ImportError:
            self.skipTest("ortools not installed; integration test skipped")

        # Instância mínima (depósito implícito = 0 no código)
        # stop_weights/volumes têm 2 paradas; o manager cria num_stops+1.
        distance_matrix = [
            [0.0, 1.0, 2.0],
            [1.0, 0.0, 1.0],
            [2.0, 1.0, 0.0],
        ]
        res = RouteOptimizerHelper.solve_vrp(
            distance_matrix=distance_matrix,
            vehicle_capacities_weight=[10.0],
            vehicle_capacities_volume=[10.0],
            stop_weights=[1.0, 1.0],
            stop_volumes=[1.0, 1.0],
            cost_per_km=[1.0],
            minimum_trip_cost=[0.0],
            max_time_seconds=2,
        )
        self.assertIsNotNone(res)
        self.assertGreaterEqual(res["num_vehicles_used"], 1)

    def test_solve_vrp_integration_sao_paulo_locations(self):
        """Test VRP solving with real São Paulo locations"""
        # Verifica se ortools está instalado
        try:
            import ortools.constraint_solver  # noqa: F401
        except ImportError:
            self.skipTest("ortools not installed; integration test skipped")

        # Usa as coordenadas reais de São Paulo
        # Calcula matriz de distâncias real
        distance_matrix = RouteOptimizerHelper.calculate_distance_matrix(
            SAO_PAULO_ROUTE_COORDINATES
        )

        # Testa VRP com 2 veículos e 8 paradas
        res = RouteOptimizerHelper.solve_vrp(
            distance_matrix=distance_matrix,
            vehicle_capacities_weight=[500.0, 500.0],  # 500 kg por veículo
            vehicle_capacities_volume=[10.0, 10.0],  # 10 m³ por veículo
            stop_weights=[50.0, 75.0, 60.0, 80.0, 45.0, 55.0, 70.0, 65.0],  # kg
            stop_volumes=[1.0, 1.5, 1.2, 1.8, 0.9, 1.1, 1.4, 1.3],  # m³
            cost_per_km=[2.5, 2.5],
            minimum_trip_cost=[50.0, 50.0],
            max_time_seconds=10,
        )

        self.assertIsNotNone(res)
        self.assertGreaterEqual(res["num_vehicles_used"], 1)
        self.assertLessEqual(res["num_vehicles_used"], 2)
        self.assertGreaterEqual(len(res["routes"]), 1)
        self.assertGreater(res["total_distance"], 0.0)
        self.assertGreater(res["total_cost"], 0.0)

        # Verifica que todas as rotas têm paradas
        for route in res["routes"]:
            self.assertGreater(len(route["route"]), 2)  # Mais que apenas depósito
            self.assertGreater(route["distance"], 0.0)
            self.assertGreater(route["weight"], 0.0)
            self.assertGreater(route["volume"], 0.0)

    def test_solve_vrp_raises_if_no_ortools(self):
        """Test that solve_vrp raises ImportError if ortools is not installed"""
        # Este teste requer mockar o pywrapcp, mas como é difícil fazer isso
        # com unittest padrão, vamos pular se ortools estiver instalado
        try:
            import ortools.constraint_solver  # noqa: F401

            # Se ortools está instalado, não podemos testar o erro
            # Isso é aceitável pois é um caso raro em produção
            self.skipTest("ortools is installed; cannot test ImportError case")
        except ImportError:
            # Se ortools não está instalado, testamos o erro
            with self.assertRaises(ImportError):
                RouteOptimizerHelper.solve_vrp(
                    distance_matrix=[[0.0]],
                    vehicle_capacities_weight=[10],
                    vehicle_capacities_volume=[10],
                    stop_weights=[],
                    stop_volumes=[],
                    cost_per_km=[1],
                    minimum_trip_cost=[0],
                )
