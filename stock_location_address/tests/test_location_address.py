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
