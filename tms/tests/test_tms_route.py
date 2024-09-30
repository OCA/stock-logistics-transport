from odoo.tests.common import TransactionCase


class TestTMSRoute(TransactionCase):
    @classmethod
    def setUpClass(self):
        super().setUpClass()

        self.uom_distance = self.env.ref("uom.product_uom_km")
        self.uom_time = self.env.ref("uom.product_uom_hour")

        # Create test locations
        self.origin_location = self.env["res.partner"].create(
            {
                "name": "Test Origin Location",
                "tms_location": True,
            }
        )

        self.destination_location = self.env["res.partner"].create(
            {
                "name": "Test Destination Location",
                "tms_location": True,
            }
        )

    def test_route_creation(self):
        route = self.env["tms.route"].create(
            {
                "name": "Test Route",
                "origin_location_id": self.origin_location.id,
                "destination_location_id": self.destination_location.id,
                "distance": 100.0,
                "estimated_time": 2.0,
                "distance_uom": self.uom_distance.id,
                "estimated_time_uom": self.uom_time.id,
            }
        )

        self.assertTrue(route, "Route wasn't created successfully")
        self.assertEqual(
            route.origin_location_id,
            self.origin_location,
            "Origin location should be correctly assigned",
        )
        self.assertEqual(
            route.destination_location_id,
            self.destination_location,
            "Destination location should be correctly assigned",
        )
        self.assertEqual(route.distance, 100.0, "Distance should be 100.0")
        self.assertEqual(route.estimated_time, 2.0, "Estimated time should be 2.0")
        self.assertEqual(
            route.distance_uom,
            self.uom_distance,
            "Distance UOM should be correctly assigned",
        )
        self.assertEqual(
            route.estimated_time_uom,
            self.uom_time,
            "Estimated time UOM should be correctly assigned",
        )

    def test_default_uom(self):
        route = self.env["tms.route"].create(
            {
                "name": "Test Route",
                "origin_location_id": self.origin_location.id,
                "destination_location_id": self.destination_location.id,
            }
        )

        self.assertEqual(
            route.estimated_time_uom, self.uom_time, "Default UOM should be hours"
        )
        self.assertEqual(
            route.distance_uom, self.uom_distance, "Default UOM should be kilometers"
        )
