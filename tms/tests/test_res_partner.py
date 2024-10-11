from odoo.tests.common import TransactionCase


class TestResPartner(TransactionCase):
    @classmethod
    def setUpClass(self):
        super().setUpClass()

        self.location = self.env["res.partner"].create(
            {
                "name": "Test Location",
                "tms_location": True,
                "location_type": "terrestrial",
            }
        )

    def test_location_creation(self):
        self.assertTrue(self.location, "Location wasn't created successfully")
        self.assertEqual(
            self.location.name,
            "Test Location",
            "Location name should be 'Test Location'",
        )
        self.assertEqual(
            self.location.location_type,
            "terrestrial",
            "Location type should be 'terrestrial'",
        )
