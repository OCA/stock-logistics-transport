from odoo.tests import TransactionCase


class TestTMSOrderStop(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Test Partner",
                "partner_latitude": -23.5505,
                "partner_longitude": -46.6333,
            }
        )
        cls.depot = cls.env["res.partner"].create(
            {
                "name": "Test Depot",
                "partner_latitude": -23.5500,
                "partner_longitude": -46.6300,
            }
        )
        cls.uom_kg = cls.env["uom.uom"].search([("name", "=", "kg")], limit=1)
        cls.uom_m3 = cls.env["uom.uom"].search(
            [("category_id.name", "=", "Volume")], limit=1
        )

    def test_create_order_stop(self):
        """Test creating a TMS order stop"""
        order = self.env["tms.order"].create(
            {
                "name": "Test Order",
                "origin_id": self.depot.id,
                "destination_id": self.depot.id,
            }
        )
        stop = self.env["tms.order.stop"].create(
            {
                "order_id": order.id,
                "partner_id": self.partner.id,
                "weight": 100.0,
                "weight_uom_id": self.uom_kg.id if self.uom_kg else None,
                "volume": 2.5,
                "volume_uom_id": self.uom_m3.id if self.uom_m3 else None,
                "unloading_time": 30,
            }
        )
        self.assertEqual(stop.order_id.id, order.id)
        self.assertEqual(stop.partner_id.id, self.partner.id)
        self.assertEqual(stop.weight, 100.0)
        self.assertEqual(stop.volume, 2.5)
        self.assertEqual(stop.state, "draft")

    def test_compute_totals(self):
        """Test computing totals for TMS order"""
        order = self.env["tms.order"].create(
            {
                "name": "Test Order",
                "origin_id": self.depot.id,
                "destination_id": self.depot.id,
            }
        )
        self.env["tms.order.stop"].create(
            {
                "order_id": order.id,
                "partner_id": self.partner.id,
                "weight": 100.0,
                "weight_uom_id": self.uom_kg.id if self.uom_kg else None,
                "volume": 2.5,
                "volume_uom_id": self.uom_m3.id if self.uom_m3 else None,
                "unloading_time": 30,
            }
        )
        self.env["tms.order.stop"].create(
            {
                "order_id": order.id,
                "partner_id": self.partner.id,
                "weight": 50.0,
                "weight_uom_id": self.uom_kg.id if self.uom_kg else None,
                "volume": 1.5,
                "volume_uom_id": self.uom_m3.id if self.uom_m3 else None,
                "unloading_time": 20,
            }
        )
        order.invalidate_recordset()
        self.assertEqual(order.total_weight, 150.0)
        self.assertEqual(order.total_volume, 4.0)
        self.assertEqual(order.total_stops, 2)

    def test_estimated_total_time(self):
        """Test computing estimated total time"""
        order = self.env["tms.order"].create(
            {
                "name": "Test Order",
                "origin_id": self.depot.id,
                "destination_id": self.depot.id,
            }
        )
        self.env["tms.order.stop"].create(
            {
                "order_id": order.id,
                "partner_id": self.partner.id,
                "weight": 100.0,
                "unloading_time": 30,
            }
        )
        self.env["tms.order.stop"].create(
            {
                "order_id": order.id,
                "partner_id": self.partner.id,
                "weight": 50.0,
                "unloading_time": 20,
            }
        )
        order.invalidate_recordset()
        # 30 + 20 = 50 minutes = 0.833 hours
        self.assertAlmostEqual(order.estimated_total_time, 50 / 60.0, places=2)

    def test_stop_address_complete(self):
        """Test computing complete address"""
        partner = self.env["res.partner"].create(
            {
                "name": "Test Partner",
                "street": "Rua Test",
                "street2": "Apt 123",
                "city": "São Paulo",
                "zip": "01310-100",
                "partner_latitude": -23.5505,
                "partner_longitude": -46.6333,
            }
        )
        order = self.env["tms.order"].create(
            {
                "name": "Test Order",
                "origin_id": self.depot.id,
                "destination_id": self.depot.id,
            }
        )
        stop = self.env["tms.order.stop"].create(
            {
                "order_id": order.id,
                "partner_id": partner.id,
                "weight": 100.0,
            }
        )
        self.assertIn("Rua Test", stop.address_complete)
        self.assertIn("Apt 123", stop.address_complete)
        self.assertIn("São Paulo", stop.address_complete)
        self.assertIn("01310-100", stop.address_complete)

    def test_create_stop_without_order(self):
        """Test creating a stop without order_id (orphan/unassigned stop)"""
        stop = self.env["tms.order.stop"].create(
            {
                "partner_id": self.partner.id,
                "weight": 75.0,
                "weight_uom_id": self.uom_kg.id if self.uom_kg else None,
                "volume": 1.0,
                "volume_uom_id": self.uom_m3.id if self.uom_m3 else None,
                "unloading_time": 15,
            }
        )
        self.assertFalse(stop.order_id)
        self.assertEqual(stop.partner_id.id, self.partner.id)
        self.assertEqual(stop.weight, 75.0)
        self.assertEqual(stop.state, "draft")

    def test_assign_stop_to_order(self):
        """Test assigning an orphan stop to an order"""
        # Create stop without order
        stop = self.env["tms.order.stop"].create(
            {
                "partner_id": self.partner.id,
                "weight": 50.0,
            }
        )
        self.assertFalse(stop.order_id)

        # Create order and assign stop
        order = self.env["tms.order"].create(
            {
                "name": "Test Order",
                "origin_id": self.depot.id,
                "destination_id": self.depot.id,
            }
        )
        stop.order_id = order.id
        self.assertEqual(stop.order_id.id, order.id)
        self.assertIn(stop, order.stop_ids)

    def test_order_delete_orphans_stop(self):
        """Test that deleting order sets stop.order_id to null (ondelete=set null)"""
        order = self.env["tms.order"].create(
            {
                "name": "Test Order",
                "origin_id": self.depot.id,
                "destination_id": self.depot.id,
            }
        )
        stop = self.env["tms.order.stop"].create(
            {
                "order_id": order.id,
                "partner_id": self.partner.id,
                "weight": 100.0,
            }
        )
        stop_id = stop.id
        self.assertEqual(stop.order_id.id, order.id)

        # Delete the order
        order.unlink()

        # Stop should still exist but without order
        stop = self.env["tms.order.stop"].browse(stop_id)
        self.assertTrue(stop.exists())
        self.assertFalse(stop.order_id)
