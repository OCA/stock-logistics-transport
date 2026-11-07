# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import AccessError
from odoo.tests.common import new_test_user

from odoo.addons.base.tests.common import BaseCommon


class TestPortalPickup(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.portal_user = new_test_user(
            cls.env,
            login="pickup_portal",
            password="pickup_portal",
            groups="base.group_portal",
        )
        cls.driver = cls.env["tms.driver"].create(
            {"name": "Portal Driver", "partner_id": cls.portal_user.partner_id.id}
        )
        cls.other_driver = cls.env["tms.driver"].create({"name": "Other Driver"})
        cls.origin = cls.env["res.partner"].create(
            {"name": "Origin", "tms_location": True}
        )
        cls.destination = cls.env["res.partner"].create(
            {"name": "Destination", "tms_location": True}
        )
        cls.kilogram = cls.env.ref("uom.product_uom_kgm")
        cls.trip = cls.env["tms.order"].create(
            {
                "name": "Portal Trip",
                "driver_id": cls.driver.id,
                "origin_id": cls.origin.id,
                "destination_id": cls.destination.id,
            }
        )
        cls.sold = cls.env["tms.cargo"].create(
            {
                "name": "Coils",
                "order_id": cls.trip.id,
                "weight": 100.0,
                "weight_uom_id": cls.kilogram.id,
            }
        )
        cls.other_trip = cls.env["tms.order"].create(
            {
                "name": "Other Trip",
                "driver_id": cls.other_driver.id,
                "origin_id": cls.origin.id,
                "destination_id": cls.destination.id,
            }
        )

    def test_portal_driver_adds_a_pickup_on_the_assigned_trip(self):
        pickup = self.trip.with_user(self.portal_user).add_pickup(
            self.sold,
            {"name": "Loaded coils", "quantity": 2, "weight": 90, "volume": 1},
        )
        self.assertEqual(pickup.parent_id, self.sold)
        self.assertEqual(pickup.order_id, self.trip)
        self.assertEqual(pickup.weight, 90)
        self.assertEqual(pickup.state, "loaded")
        self.assertFalse(pickup.sale_line_id)

    def test_portal_driver_cannot_read_another_trip(self):
        trip = self.other_trip.with_user(self.portal_user)
        self.assertFalse(trip.search([("id", "=", self.other_trip.id)]))
        with self.assertRaises(AccessError):
            trip.check_access("read")

    def test_portal_driver_cannot_record_a_pickup_on_another_trip(self):
        with self.assertRaises(AccessError):
            self.other_trip.with_user(self.portal_user).add_pickup(
                self.sold, {"name": "Wrong", "weight": 1}
            )
