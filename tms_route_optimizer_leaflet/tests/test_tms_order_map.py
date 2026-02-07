# Copyright (C) 2025 KMEE (https://kmee.com.br)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests.common import TransactionCase


class TestTMSOrderMap(TransactionCase):
    """Tests for TMS Order Leaflet map visualization fields."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        cls.partner_origin = cls.env["res.partner"].create(
            {
                "name": "Warehouse SP",
                "partner_latitude": -23.5505,
                "partner_longitude": -46.6333,
            }
        )
        cls.partner_dest = cls.env["res.partner"].create(
            {
                "name": "Customer RJ",
                "partner_latitude": -22.9068,
                "partner_longitude": -43.1729,
            }
        )
        cls.partner_stop1 = cls.env["res.partner"].create(
            {
                "name": "Stop Campinas",
                "partner_latitude": -22.9099,
                "partner_longitude": -47.0626,
            }
        )
        cls.partner_stop2 = cls.env["res.partner"].create(
            {
                "name": "Stop Sorocaba",
                "partner_latitude": -23.5015,
                "partner_longitude": -47.4526,
            }
        )

    def _create_order(self, **kwargs):
        vals = {
            "origin_id": self.partner_origin.id,
            "destination_id": self.partner_dest.id,
        }
        vals.update(kwargs)
        return self.env["tms.order"].create(vals)

    def test_compute_map_coordinates_with_origin(self):
        """Map coordinates should come from the origin partner."""
        order = self._create_order()
        self.assertAlmostEqual(order.map_latitude, -23.5505, places=3)
        self.assertAlmostEqual(order.map_longitude, -46.6333, places=3)

    def test_compute_map_coordinates_without_origin(self):
        """Map coordinates should be 0.0 when no origin is set."""
        order = self.env["tms.order"].create({})
        self.assertEqual(order.map_latitude, 0.0)
        self.assertEqual(order.map_longitude, 0.0)

    def test_compute_map_display(self):
        """Display address should include origin and destination."""
        order = self._create_order()
        self.assertIn("Warehouse SP", order.map_display_address)
        self.assertIn("Customer RJ", order.map_display_address)

    def test_compute_route_summary_no_stops(self):
        """Route summary should be empty when there are no stops."""
        order = self.env["tms.order"].create({})
        self.assertEqual(order.route_summary, "")

    def test_compute_route_summary_with_stops(self):
        """Route summary should count stops including auto-created endpoints."""
        order = self._create_order()
        # _create_endpoint_stops auto-creates origin+destination stops = 2
        base_count = len(order.stop_ids)
        self.env["tms.order.stop"].create(
            {
                "order_id": order.id,
                "partner_id": self.partner_stop1.id,
                "sequence": 10,
            }
        )
        self.env["tms.order.stop"].create(
            {
                "order_id": order.id,
                "partner_id": self.partner_stop2.id,
                "sequence": 20,
            }
        )
        order.invalidate_recordset()
        expected = f"{base_count + 2} stops"
        self.assertIn(expected, order.route_summary)

    def test_get_route_coordinates_ordering(self):
        """Route coordinates should include origin, stops in order, destination."""
        order = self._create_order()
        self.env["tms.order.stop"].create(
            {
                "order_id": order.id,
                "partner_id": self.partner_stop1.id,
                "sequence": 1,
            }
        )
        self.env["tms.order.stop"].create(
            {
                "order_id": order.id,
                "partner_id": self.partner_stop2.id,
                "sequence": 2,
            }
        )
        order.invalidate_recordset()
        coords = order._get_route_coordinates()

        # Should have: origin + 2 stops + destination = 4 points
        self.assertEqual(len(coords), 4)
        # First point should be origin
        self.assertAlmostEqual(coords[0][0], -23.5505, places=3)
        # Last point should be destination
        self.assertAlmostEqual(coords[-1][0], -22.9068, places=3)

    def test_get_route_coordinates_without_stops(self):
        """Route coordinates should include only origin and destination."""
        order = self._create_order()
        coords = order._get_route_coordinates()
        self.assertEqual(len(coords), 2)

    def test_action_open_route_map(self):
        """action_open_route_map should return a valid action dict."""
        order = self._create_order()
        action = order.action_open_route_map()
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["res_model"], "tms.order")
        self.assertIn("leaflet_map", action["view_mode"])

    def test_action_open_stops_map(self):
        """action_open_stops_map should return a valid action dict."""
        order = self._create_order()
        action = order.action_open_stops_map()
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["res_model"], "tms.order.stop")
