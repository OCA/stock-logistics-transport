# Copyright (C) 2024 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase


class TestTMSDeliveryStopsDemo(TransactionCase):
    """Test TMS Delivery Stops using demo data"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Use demo data
        cls.depot = cls.env.ref("tms_delivery_stops.demo_depot_location")
        cls.partner_1 = cls.env.ref("tms_delivery_stops.demo_partner_delivery_1")
        cls.partner_2 = cls.env.ref("tms_delivery_stops.demo_partner_delivery_2")
        cls.partner_3 = cls.env.ref("tms_delivery_stops.demo_partner_delivery_3")
        cls.order = cls.env.ref("tms_delivery_stops.demo_tms_order_with_stops_1")
        cls.stop_1 = cls.env.ref("tms_delivery_stops.demo_tms_order_stop_1")
        cls.stop_2 = cls.env.ref("tms_delivery_stops.demo_tms_order_stop_2")
        cls.stop_3 = cls.env.ref("tms_delivery_stops.demo_tms_order_stop_3")

    def test_demo_depot_exists(self):
        """Test that demo depot location exists"""
        self.assertTrue(self.depot)
        self.assertEqual(self.depot.name, "Depósito Central - São Paulo")
        self.assertIsNotNone(self.depot.partner_latitude)
        self.assertIsNotNone(self.depot.partner_longitude)

    def test_demo_partners_have_geolocation(self):
        """Test that demo partners have geolocation"""
        for partner in [self.partner_1, self.partner_2, self.partner_3]:
            self.assertIsNotNone(
                partner.partner_latitude, f"Partner {partner.name} missing latitude"
            )
            self.assertIsNotNone(
                partner.partner_longitude, f"Partner {partner.name} missing longitude"
            )

    def test_demo_order_has_stops(self):
        """Test that demo order has stops"""
        self.assertTrue(self.order)
        self.assertEqual(self.order.name, "ORD-DEMO-001")
        self.assertGreater(len(self.order.stop_ids), 0)

    def test_demo_stops_have_data(self):
        """Test that demo stops have required data"""
        for stop in [self.stop_1, self.stop_2, self.stop_3]:
            self.assertTrue(stop.partner_id)
            self.assertGreater(stop.weight, 0)
            self.assertGreater(stop.volume, 0)
            self.assertIsNotNone(stop.latitude)
            self.assertIsNotNone(stop.longitude)
            self.assertEqual(stop.state, "draft")

    def test_demo_order_totals(self):
        """Test that demo order totals are computed correctly"""
        self.order.invalidate_recordset()
        expected_weight = sum(self.order.stop_ids.mapped("weight"))
        expected_volume = sum(self.order.stop_ids.mapped("volume"))
        self.assertEqual(self.order.total_weight, expected_weight)
        self.assertEqual(self.order.total_volume, expected_volume)
        self.assertEqual(self.order.total_stops, len(self.order.stop_ids))

    def test_demo_stops_address_complete(self):
        """Test that demo stops have complete address"""
        for stop in [self.stop_1, self.stop_2, self.stop_3]:
            self.assertTrue(stop.address_complete)
            self.assertIn(stop.partner_id.city, stop.address_complete)

    def test_demo_order_estimated_time(self):
        """Test that demo order estimated time is computed"""
        self.order.invalidate_recordset()
        expected_time = sum(self.order.stop_ids.mapped("unloading_time")) / 60.0
        self.assertAlmostEqual(self.order.estimated_total_time, expected_time, places=2)
