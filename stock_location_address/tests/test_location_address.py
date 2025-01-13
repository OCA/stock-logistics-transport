#  Copyright 2018 Creu Blanca
#  License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.tests import TransactionCase


class TestLocationAddress(TransactionCase):
    def test_inheritance(self):
        partner_1 = self.env["res.partner"].create({"name": "Partner1"})
        partner_2 = self.env["res.partner"].create({"name": "Partner2"})
        parent_location = self.env["stock.location"].create(
            {"name": "Parent", "usage": "internal", "address_id": partner_1.id}
        )
        location = self.env["stock.location"].create(
            {"name": "Location", "usage": "internal", "location_id": parent_location.id}
        )
        self.assertEqual(location.real_address_id, partner_1)
        location.address_id = partner_2
        self.assertEqual(location.real_address_id, partner_2)

    def test_parent_without_address(self):
        partner_1 = self.env["res.partner"].create({"name": "Partner1"})
        parent_location_no_address = self.env["stock.location"].create(
            {"name": "Parent", "usage": "internal"}
        )
        location = self.env["stock.location"].create(
            {
                "name": "Location",
                "usage": "internal",
                "location_id": parent_location_no_address.id,
            }
        )

        # Assert that the real_address_id is empty when no addresses are set
        self.assertFalse(location.real_address_id)
        # Assert that the child inherits the parent's address
        parent_location_no_address.address_id = partner_1
        self.assertEqual(location.real_address_id, partner_1)

    def test_multi_level_hierarchy(self):
        partner_1 = self.env["res.partner"].create({"name": "Partner1"})
        partner_2 = self.env["res.partner"].create({"name": "Partner2"})
        grandparent_location = self.env["stock.location"].create(
            {"name": "Grandparent", "usage": "internal", "address_id": partner_1.id}
        )
        parent_location = self.env["stock.location"].create(
            {
                "name": "Parent",
                "usage": "internal",
                "location_id": grandparent_location.id,
            }
        )
        location = self.env["stock.location"].create(
            {"name": "Child", "usage": "internal", "location_id": parent_location.id}
        )

        # Assert that the child's real_address_id inherits from the grandparent
        self.assertEqual(location.real_address_id, partner_1)
        # Assert that the child now inherits from the parent instead of the grandparent
        parent_location.address_id = partner_2
        self.assertEqual(location.real_address_id, partner_2)
