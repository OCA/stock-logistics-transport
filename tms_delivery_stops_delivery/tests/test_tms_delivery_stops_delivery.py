# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase


class TestTmsRouteOptimizerDelivery(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Test Partner",
                "partner_latitude": 10.0,
                "partner_longitude": 20.0,
            }
        )
        cls.delivery_product = cls.env["product.product"].create(
            {
                "name": "Delivery Product",
                "type": "service",
            }
        )
        cls.carrier = cls.env["delivery.carrier"].create(
            {
                "name": "Internal Carrier",
                "delivery_type": "fixed",
                "product_id": cls.delivery_product.id,
                "is_internal_carrier": True,
                "auto_create_stops": True,
            }
        )
        cls.team = cls.env["tms.team"].create({"name": "Test Team"})

        cls.product = cls.env["product.product"].create(
            {
                "name": "Test Product",
                "type": "consu",
                "weight": 1.5,
                "volume": 0.4,
            }
        )
        cls.uom_unit = cls.env.ref("uom.product_uom_unit")
        cls.picking_type = cls.env.ref(
            "stock.picking_type_out", raise_if_not_found=False
        ) or cls.env["stock.picking.type"].search([("code", "=", "outgoing")], limit=1)
        cls.location_src = cls.picking_type.default_location_src_id or cls.env.ref(
            "stock.stock_location_stock"
        )
        cls.location_dest = cls.picking_type.default_location_dest_id or cls.env.ref(
            "stock.stock_location_customers"
        )

    def _get_picking_type(self, code):
        picking_type = self.env.ref(
            f"stock.picking_type_{code}", raise_if_not_found=False
        )
        if not picking_type:
            picking_type = self.env["stock.picking.type"].search(
                [("code", "=", code)], limit=1
            )
        return picking_type

    def _get_picking_locations(self, picking_type):
        location_src = picking_type.default_location_src_id or self.env.ref(
            "stock.stock_location_stock"
        )
        location_dest = picking_type.default_location_dest_id or self.env.ref(
            "stock.stock_location_customers"
        )
        return location_src, location_dest

    def _create_picking(
        self, partner=None, carrier=None, picking_type=None, product=None
    ):
        partner = partner or self.partner
        carrier = carrier or self.carrier
        picking_type = picking_type or self.picking_type
        product = product or self.product
        location_src, location_dest = self._get_picking_locations(picking_type)

        picking = self.env["stock.picking"].create(
            {
                "partner_id": partner.id,
                "picking_type_id": picking_type.id,
                "location_id": location_src.id,
                "location_dest_id": location_dest.id,
                "carrier_id": carrier.id,
            }
        )
        self.env["stock.move"].create(
            {
                "name": "Test Move",
                "product_id": product.id,
                "product_uom_qty": 2.0,
                "product_uom": self.uom_unit.id,
                "location_id": location_src.id,
                "location_dest_id": location_dest.id,
                "picking_id": picking.id,
            }
        )
        return picking

    def test_auto_create_tms_stop_on_confirm(self):
        picking = self._create_picking()
        picking.action_confirm()

        self.assertTrue(picking.tms_stop_id)
        self.assertEqual(picking.tms_stop_id.picking_id, picking)
        self.assertFalse(picking.tms_stop_id.order_id)

    def test_sync_stop_state_on_done(self):
        picking = self._create_picking()
        picking.action_confirm()
        stop = picking.tms_stop_id

        picking.write({"state": "done"})
        self.assertEqual(stop.state, "scheduled")

    def test_stop_without_geolocation(self):
        partner_no_geo = self.env["res.partner"].create({"name": "No Geo Partner"})
        picking = self._create_picking(partner=partner_no_geo)
        picking.action_confirm()

        self.assertTrue(picking.tms_stop_id)
        bodies = " ".join(picking.message_ids.mapped("body")).lower()
        self.assertIn("no geolocation", bodies)

    def test_no_stop_for_non_outgoing(self):
        picking_type_in = self._get_picking_type("incoming")
        if not picking_type_in:
            self.skipTest("Incoming picking type not found.")
        picking = self._create_picking(picking_type=picking_type_in)
        picking.action_confirm()
        self.assertFalse(picking.tms_stop_id)

    def test_no_stop_for_return_picking(self):
        picking = self._create_picking()
        if "is_return_picking" not in picking._fields:
            self.skipTest("Return picking field not available.")
        try:
            picking.write({"is_return_picking": True})
        except Exception:
            self.skipTest("Return picking flag is read-only.")
        picking.action_confirm()
        self.assertFalse(picking.tms_stop_id)

    def test_no_stop_for_external_carrier(self):
        external_carrier = self.env["delivery.carrier"].create(
            {
                "name": "External Carrier",
                "delivery_type": "fixed",
                "product_id": self.delivery_product.id,
                "is_internal_carrier": False,
                "auto_create_stops": True,
            }
        )
        picking = self._create_picking(carrier=external_carrier)
        picking.action_confirm()
        self.assertFalse(picking.tms_stop_id)

    def test_sync_stop_state_on_cancel(self):
        picking = self._create_picking()
        picking.action_confirm()
        stop = picking.tms_stop_id

        picking.write({"state": "cancel"})
        self.assertEqual(stop.state, "skipped")

    def test_wizard_manual_plan(self):
        picking_one = self._create_picking()
        picking_two = self._create_picking()
        (picking_one + picking_two).action_confirm()
        (picking_one + picking_two).mapped("tms_stop_id").write({"state": "scheduled"})

        wizard = self.env["tms.order.from.pickings"].create(
            {
                "mode": "manual_plan",
                "picking_ids": [(6, 0, (picking_one + picking_two).ids)],
                "tms_team_id": self.team.id,
            }
        )
        wizard.action_create_order()

        self.assertEqual(
            (picking_one + picking_two).mapped("tms_stop_id.state"),
            ["draft", "draft"],
        )

    def test_wizard_existing_order(self):
        picking_one = self._create_picking()
        picking_two = self._create_picking()
        (picking_one + picking_two).action_confirm()

        order = self.env["tms.order"].create(
            {
                "name": "Existing Order",
                "tms_team_id": self.team.id,
            }
        )
        wizard = self.env["tms.order.from.pickings"].create(
            {
                "mode": "existing_order",
                "picking_ids": [(6, 0, (picking_one + picking_two).ids)],
                "existing_order_id": order.id,
            }
        )
        wizard.action_create_order()

        self.assertEqual(
            (picking_one + picking_two).mapped("tms_stop_id.order_id"),
            order,
        )

    def test_volume_from_picking(self):
        volume_product = self.env["product.product"].create(
            {
                "name": "Volume Product",
                "type": "consu",
                "volume": 0.6,
                "uom_id": self.uom_unit.id,
                "uom_po_id": self.uom_unit.id,
            }
        )
        picking = self._create_picking(product=volume_product)
        picking.action_confirm()

        self.assertTrue(picking.tms_stop_id)
        self.assertEqual(picking.tms_stop_id.volume, picking.volume)

    def test_wizard_creates_order_for_stops(self):
        picking_one = self._create_picking()
        picking_two = self._create_picking()
        (picking_one + picking_two).action_confirm()

        wizard = self.env["tms.order.from.pickings"].create(
            {
                "mode": "new_order",
                "picking_ids": [(6, 0, (picking_one + picking_two).ids)],
                "tms_team_id": self.team.id,
            }
        )
        action = wizard.action_create_order()
        order = self.env["tms.order"].browse(action["res_id"])

        self.assertTrue(order)
        self.assertEqual(
            (picking_one + picking_two).mapped("tms_stop_id.order_id"),
            order,
        )
