from odoo.exceptions import UserError
from odoo.tests import TransactionCase


class TestStopWorkflowSync(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_a = cls.env["res.partner"].create(
            {
                "name": "Partner A",
                "partner_latitude": -23.55,
                "partner_longitude": -46.63,
            }
        )
        cls.partner_b = cls.env["res.partner"].create(
            {
                "name": "Partner B",
                "partner_latitude": -23.56,
                "partner_longitude": -46.64,
            }
        )
        cls.depot = cls.env["res.partner"].create(
            {
                "name": "Test Depot",
                "tms_location": True,
                "partner_latitude": -23.50,
                "partner_longitude": -46.60,
            }
        )
        # Ensure vehicle/driver security checks are disabled
        cls.env["ir.config_parameter"].sudo().set_param(
            "tms.default_vehicle_insurance_security_days", "0"
        )
        cls.env["ir.config_parameter"].sudo().set_param(
            "tms.default_driver_license_security_days", "0"
        )
        cls.completed_stage = cls.env.ref("tms.tms_stage_order_completed")
        cls.draft_stage = cls.env.ref("tms.tms_stage_order_draft")

    def _create_order_with_stops(self, stop_count=2):
        """Helper to create an order with delivery stops."""
        order = self.env["tms.order"].create(
            {
                "name": "Test Order",
                "origin_id": self.depot.id,
                "destination_id": self.depot.id,
            }
        )
        partners = [self.partner_a, self.partner_b]
        stops = self.env["tms.order.stop"]
        for i in range(stop_count):
            stops |= self.env["tms.order.stop"].create(
                {
                    "order_id": order.id,
                    "partner_id": partners[i % len(partners)].id,
                    "weight": 10.0,
                    "sequence": (i + 1) * 10,
                }
            )
        return order, stops

    def test_action_deliver(self):
        """action_deliver changes state to delivered and sets delivered_date."""
        _order, stops = self._create_order_with_stops(1)
        stop = stops[0]
        self.assertEqual(stop.state, "draft")
        self.assertFalse(stop.delivered_date)

        stop.action_deliver()

        self.assertEqual(stop.state, "delivered")
        self.assertTrue(stop.delivered_date)

    def test_action_skip(self):
        """action_skip changes state to skipped."""
        _order, stops = self._create_order_with_stops(1)
        stop = stops[0]
        stop.action_skip()
        self.assertEqual(stop.state, "skipped")

    def test_cannot_deliver_skipped(self):
        """UserError when trying to deliver a skipped stop."""
        _order, stops = self._create_order_with_stops(1)
        stop = stops[0]
        stop.action_skip()
        with self.assertRaises(UserError):
            stop.action_deliver()

    def test_cannot_skip_delivered(self):
        """UserError when trying to skip a delivered stop."""
        _order, stops = self._create_order_with_stops(1)
        stop = stops[0]
        stop.action_deliver()
        with self.assertRaises(UserError):
            stop.action_skip()

    def test_all_delivered_auto_completes_order(self):
        """Order auto-completes when all delivery stops are delivered."""
        order, stops = self._create_order_with_stops(2)
        self.assertNotEqual(order.stage_id, self.completed_stage)

        stops[0].action_deliver()
        order.invalidate_recordset()
        self.assertNotEqual(order.stage_id, self.completed_stage)

        stops[1].action_deliver()
        order.invalidate_recordset()
        self.assertEqual(order.stage_id, self.completed_stage)

    def test_mixed_delivered_skipped_auto_completes(self):
        """delivered + skipped = order auto-completes."""
        order, stops = self._create_order_with_stops(2)

        stops[0].action_deliver()
        stops[1].action_skip()

        order.invalidate_recordset()
        self.assertEqual(order.stage_id, self.completed_stage)

    def test_partial_no_auto_complete(self):
        """Some stops pending means order does not auto-complete."""
        order, stops = self._create_order_with_stops(2)

        stops[0].action_deliver()

        order.invalidate_recordset()
        self.assertNotEqual(order.stage_id, self.completed_stage)

    def test_auto_complete_preserves_skipped_states(self):
        """Skipped stops remain skipped when order auto-completes."""
        order, stops = self._create_order_with_stops(2)

        stops[0].action_skip()
        stops[1].action_deliver()

        order.invalidate_recordset()
        self.assertEqual(order.stage_id, self.completed_stage)
        # Skipped stop must remain skipped (not overwritten to delivered)
        stops[0].invalidate_recordset()
        self.assertEqual(stops[0].state, "skipped")
        stops[1].invalidate_recordset()
        self.assertEqual(stops[1].state, "delivered")

    def test_manual_stage_syncs_stops(self):
        """Manually changing stage_id propagates stop_state_sync to stops."""
        # Create a stage with stop_state_sync = 'scheduled'
        sync_stage = self.env["tms.stage"].create(
            {
                "name": "In Transit",
                "sequence": 15,
                "stage_type": "order",
                "stop_state_sync": "scheduled",
            }
        )
        order, stops = self._create_order_with_stops(2)
        self.assertEqual(stops[0].state, "draft")

        order.write({"stage_id": sync_stage.id})

        stops.invalidate_recordset()
        self.assertEqual(stops[0].state, "scheduled")
        self.assertEqual(stops[1].state, "scheduled")

    def test_start_trip_schedules_stops(self):
        """button_start_order transitions draft stops to scheduled."""
        order, stops = self._create_order_with_stops(2)
        self.assertEqual(stops[0].state, "draft")
        self.assertEqual(stops[1].state, "draft")

        order.button_start_order()

        stops.invalidate_recordset()
        self.assertEqual(stops[0].state, "scheduled")
        self.assertEqual(stops[1].state, "scheduled")

    def test_end_trip_delivers_and_completes(self):
        """button_end_order delivers remaining stops and auto-completes."""
        order, stops = self._create_order_with_stops(2)
        # Start the trip first so date_start is set (required by button_end_order)
        order.button_start_order()

        # Deliver one stop manually
        stops[0].action_deliver()

        order.button_end_order()

        stops.invalidate_recordset()
        order.invalidate_recordset()
        # First stop was already delivered - should stay delivered
        self.assertEqual(stops[0].state, "delivered")
        # Second stop was scheduled - should now be delivered
        self.assertEqual(stops[1].state, "delivered")
        self.assertTrue(stops[1].delivered_date)
        # Order should be auto-completed
        self.assertEqual(order.stage_id, self.completed_stage)

    def test_orphan_stop_deliver_no_error(self):
        """A stop without order can be delivered without error."""
        stop = self.env["tms.order.stop"].create(
            {
                "partner_id": self.partner_a.id,
                "weight": 5.0,
            }
        )
        stop.action_deliver()
        self.assertEqual(stop.state, "delivered")
        self.assertTrue(stop.delivered_date)

    def test_no_delivery_stops_no_auto_complete(self):
        """Order with only origin/destination does not auto-complete."""
        order = self.env["tms.order"].create(
            {
                "name": "Test Order",
                "origin_id": self.depot.id,
                "destination_id": self.depot.id,
            }
        )
        # Order has origin + destination stops but no delivery stops
        origin_stop = order.stop_ids.filtered(lambda s: s.stop_type == "origin")
        dest_stop = order.stop_ids.filtered(lambda s: s.stop_type == "destination")
        self.assertTrue(origin_stop)
        self.assertTrue(dest_stop)
        self.assertFalse(order.stop_ids.filtered(lambda s: s.stop_type == "delivery"))

        # Deliver the endpoint stops — should not trigger auto-complete
        origin_stop.action_deliver()
        dest_stop.action_deliver()

        order.invalidate_recordset()
        self.assertNotEqual(order.stage_id, self.completed_stage)
