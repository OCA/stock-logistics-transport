# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestCargoWrite(TransactionCase):
    def test_setting_the_trip_does_not_recurse(self):
        cargo = self.env["tms.cargo"].create({"name": "Boxes", "weight": 10})
        pickup = self.env["tms.cargo"].create(
            {"name": "Loaded boxes", "parent_id": cargo.id, "weight": 12}
        )
        trip = self.env["tms.order"].create({"name": "Pickup trip"})
        cargo.write({"order_id": trip.id})
        self.assertEqual(cargo.order_id, trip)
        self.assertEqual(pickup.order_id, trip)
        self.assertEqual(pickup.sold_cargo_id, cargo)
        self.assertFalse(cargo.sold_cargo_id)

    def test_sold_shipment_shows_itself(self):
        partner = self.env["res.partner"].create({"name": "Buyer"})
        order = self.env["sale.order"].create({"partner_id": partner.id})
        product = self.env["product.product"].create(
            {"name": "Haul", "type": "service"}
        )
        line = self.env["sale.order.line"].create(
            {
                "order_id": order.id,
                "product_id": product.id,
                "product_uom_qty": 1,
            }
        )
        cargo = self.env["tms.cargo"].create(
            {"name": "Boxes", "sale_line_id": line.id, "weight": 10}
        )
        self.assertFalse(cargo.parent_id)
        self.assertEqual(cargo.sold_cargo_id, cargo)
