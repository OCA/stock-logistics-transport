# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.base.tests.common import BaseCommon


class TestProductTemplate(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.vehicle_model = cls.env["fleet.vehicle.model"].create(
            {
                "name": "Test Model",
                "brand_id": cls.env["fleet.vehicle.model.brand"]
                .create({"name": "Test Brand"})
                .id,
                "vehicle_type": "car",
            }
        )

    def test_service_product_clears_tms_vehicle(self):
        product = self.env["product.template"].create(
            {
                "name": "Trip Service",
                "type": "consu",
                "tms_vehicle": True,
            }
        )
        product.type = "service"
        self.assertFalse(product.tms_vehicle)

    def test_goods_product_clears_transport_type(self):
        product = self.env["product.template"].create(
            {
                "name": "Vehicle Product",
                "type": "service",
                "transport_type": "cargo",
                "transit_mode": "road",
                "booking_type": "full_asset",
            }
        )
        product.type = "consu"
        self.assertFalse(product.transport_type)
        self.assertFalse(product.transit_mode)
        self.assertFalse(product.booking_type)

    def test_booking_type_selection(self):
        selection = self.env["product.template"].fields_get(["booking_type"])[
            "booking_type"
        ]["selection"]
        self.assertEqual(
            selection,
            [
                ("shared_space", "Shared space"),
                ("full_asset", "Full asset"),
            ],
        )

    def test_transport_type_includes_none(self):
        selection = self.env["product.template"].fields_get(["transport_type"])[
            "transport_type"
        ]["selection"]
        self.assertEqual(
            selection,
            [
                ("none", "None"),
                ("cargo", "Cargo"),
                ("passenger", "Passenger"),
            ],
        )

    def test_service_defaults_transport_type_to_none(self):
        product = self.env["product.template"].create(
            {"name": "Plain Service", "type": "service"}
        )
        self.assertEqual(product.transport_type, "none")
        self.assertFalse(product.transit_mode)
        self.assertFalse(product.booking_type)

    def test_passenger_services_keep_booking_and_network(self):
        services = {
            "tms_product.product_tms_charter_service": ("road", "full_asset"),
            "tms_product.product_tms_cabin_service": ("air", "shared_space"),
            "tms_product.product_tms_seat_service": ("road", "shared_space"),
            "tms_product.product_tms_train_charter_service": ("rail", "full_asset"),
            "tms_product.product_tms_train_seat_service": ("rail", "shared_space"),
        }
        for xmlid, (mode, booking) in services.items():
            product = self.env.ref(xmlid)
            self.assertEqual(product.type, "service")
            self.assertEqual(product.transport_type, "passenger")
            self.assertEqual(product.transit_mode, mode)
            self.assertEqual(product.booking_type, booking)

    def test_rail_cargo_services(self):
        services = {
            "tms_product.product_tms_rail_service": "full_asset",
            "tms_product.product_tms_rail_consolidation_service": "shared_space",
        }
        for xmlid, booking in services.items():
            product = self.env.ref(xmlid)
            self.assertEqual(product.type, "service")
            self.assertEqual(product.transport_type, "cargo")
            self.assertEqual(product.transit_mode, "rail")
            self.assertEqual(product.booking_type, booking)

    def test_transit_mode_selection(self):
        selection = self.env["product.template"].fields_get(["transit_mode"])[
            "transit_mode"
        ]["selection"]
        self.assertEqual(
            selection,
            [
                ("air", "Air"),
                ("water", "Water"),
                ("road", "Road"),
                ("rail", "Rail"),
            ],
        )

    def test_disabled_mode_drops_out_of_the_selection(self):
        self.env["res.config.settings"].create(
            {"group_tms_rail_user": False}
        ).set_values()
        user = self.env["res.users"].create(
            {
                "name": "No Rail",
                "login": "no_rail_mode",
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        selection = (
            self.env["product.template"]
            .with_user(user)
            .fields_get(["transit_mode"])["transit_mode"]["selection"]
        )
        modes = [key for key, _label in selection]
        self.assertNotIn("rail", modes)
        self.assertIn("road", modes)

    def test_cargo_labels_follow_the_transport_type(self):
        product = self.env["product.template"].create(
            {
                "name": "Trip Service",
                "type": "service",
                "transport_type": "cargo",
                "transit_mode": "air",
                "booking_type": "full_asset",
            }
        )
        self.assertEqual(product.transit_mode_cargo, "air")
        product.transport_type = "passenger"
        product.transit_mode_passenger = "road"
        self.assertEqual(product.transit_mode, "road")
        product.transport_type = "none"
        self.assertFalse(product.transit_mode)
        self.assertFalse(product.booking_type)

    def test_transport_mode_visibility(self):
        arch = self.env.ref("tms_product.product_template_form_view").arch
        self.assertIn("transit_mode_cargo", arch)
        self.assertIn("transit_mode_passenger", arch)
        self.assertIn("booking_type", arch)

    def test_network_stays_when_the_business_switches(self):
        product = self.env["product.template"].create(
            {
                "name": "Trip Service",
                "type": "service",
                "transport_type": "cargo",
                "transit_mode": "air",
                "booking_type": "full_asset",
            }
        )
        product.transport_type = "passenger"
        self.assertEqual(product.transit_mode, "air")
        self.assertEqual(product.transit_mode_passenger, "air")

    def test_vehicle_type_selection(self):
        selection = self.env["product.template"]._compute_vehicle_type_selection()
        fleet_selection = self.env["fleet.vehicle.model"].fields_get(["vehicle_type"])[
            "vehicle_type"
        ]["selection"]
        self.assertEqual(selection, fleet_selection)

    def test_vehicle_fields_on_template(self):
        product = self.env["product.template"].create(
            {
                "name": "Vehicle Product",
                "type": "consu",
                "tms_vehicle": True,
                "vehicle_type": "car",
                "model_id": self.vehicle_model.id,
            }
        )
        self.assertTrue(product.tms_vehicle)
        self.assertEqual(product.vehicle_type, "car")
        self.assertEqual(product.model_id, self.vehicle_model)

    def test_vehicle_fields_cleared_when_not_trip_product(self):
        product = self.env["product.template"].create(
            {
                "name": "Vehicle Product",
                "type": "consu",
                "tms_vehicle": True,
                "vehicle_type": "car",
                "model_id": self.vehicle_model.id,
                "transport_type": False,
            }
        )
        product._compute_restore_vehicle_fields()
        self.assertFalse(product.vehicle_type)
        self.assertFalse(product.model_id)
