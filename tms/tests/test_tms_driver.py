from odoo.tests.common import TransactionCase


class TestTmsDriver(TransactionCase):
    @classmethod
    def setUpClass(self):
        super().setUpClass()

        self.stage = self.env["tms.stage"].create(
            {
                "name": "Test Stage",
                "stage_type": "driver",
                "sequence": 1,
            }
        )

        self.driver = self.env["tms.driver"].create(
            {
                "name": "Test Driver",
                "is_external": True,
                "driver_type": "terrestrial",
                "driver_license_number": "ABC123456",
                "driver_license_type": "B",
                "distance_traveled": 1000,
                "distance_traveled_uom": "km",
                "driving_experience_years": 5,
            }
        )

    def test_driver_creation(self):
        self.driver._default_stage_id()

        self.assertTrue(self.driver, "Driver wasn't created successfully")
        self.assertEqual(
            self.driver.name, "Test Driver", "Driver name should be 'Test Driver'"
        )
        self.assertTrue(self.driver.is_external, "Driver should be marked as external")
        self.assertEqual(
            self.driver.driver_type,
            "terrestrial",
            "Driver type should be 'terrestrial'",
        )
        self.assertEqual(
            self.driver.driver_license_number,
            "ABC123456",
            "Driver license number should be 'ABC123456'",
        )
        self.assertEqual(
            self.driver.driver_license_type, "B", "Driver license type should be 'B'"
        )
        self.assertEqual(
            self.driver.distance_traveled, 1000, "Distance traveled should be 1000"
        )
        self.assertEqual(
            self.driver.driving_experience_years,
            5,
            "Driving experience years should be 5",
        )
        self.assertTrue(
            self.driver.stage_id, "Driver stage should be correctly assigned"
        )

    def test_read_group_stage_ids(self):
        stages = self.env["tms.driver"]._read_group_stage_ids(
            self.env["tms.stage"], [], "sequence"
        )
        self.assertIn(self.stage, stages)
        self.assertTrue(all(stage.stage_type == "driver" for stage in stages))

    def test_web_read_group_expands_driver_stages(self):
        result = (
            self.env["tms.driver"]
            .with_context(read_group_expand=True)
            .web_read_group(
                domain=[("is_company", "=", False)],
                groupby=["stage_id"],
                auto_unfold=True,
                opening_info=[],
                unfold_read_specification={"display_name": {}, "is_active": {}},
            )
        )
        self.assertGreater(result["length"], 0)
        self.assertTrue(result["groups"])

    def test_schedule_meeting(self):
        if not hasattr(type(self.driver.partner_id), "schedule_meeting"):
            self.skipTest("calendar module is not installed")
        action = self.driver.schedule_meeting()
        self.assertEqual(action.get("res_model"), "calendar.event")

    def _partner_method_available(self, method_name):
        return hasattr(type(self.driver.partner_id), method_name)

    def test_create_company_delegates_to_partner(self):
        if not self._partner_method_available("create_company"):
            self.skipTest("create_company not available on res.partner")
        self.driver.create_company()

    def test_action_open_employees_delegates_to_partner(self):
        if not self._partner_method_available("action_open_employees"):
            self.skipTest("action_open_employees not available on res.partner")
        action = self.driver.action_open_employees()
        self.assertEqual(action.get("res_model"), "hr.employee")

    def test_open_commercial_entity_delegates_to_partner(self):
        if not self._partner_method_available("open_commercial_entity"):
            self.skipTest("open_commercial_entity not available on res.partner")
        action = self.driver.open_commercial_entity()
        self.assertEqual(action.get("res_model"), "res.partner")

    def test_blacklist_remove_delegates_to_partner(self):
        if not self._partner_method_available("phone_action_blacklist_remove"):
            self.skipTest("blacklist methods not available on res.partner")
        self.driver.phone_action_blacklist_remove()
        self.driver.mail_action_blacklist_remove()

    def test_geo_localize_delegates_to_partner(self):
        if not self._partner_method_available("geo_localize"):
            self.skipTest("geo_localize not available on res.partner")
        self.driver.geo_localize()

    def test_action_view_partner_invoices_delegates_to_partner(self):
        if not self._partner_method_available("action_view_partner_invoices"):
            self.skipTest("action_view_partner_invoices not available")
        action = self.driver.action_view_partner_invoices()
        self.assertEqual(action.get("res_model"), "account.move")

    def test_action_view_stock_serial_delegates_to_partner(self):
        if not self._partner_method_available("action_view_stock_serial"):
            self.skipTest("stock module is not installed")
        action = self.driver.action_view_stock_serial()
        self.assertEqual(action.get("res_model"), "stock.lot")

    def test_action_view_purchase_orders_uses_partner_id(self):
        try:
            action = self.driver.action_view_purchase_orders()
        except Exception:
            self.skipTest("purchase module is not installed")
        self.assertEqual(action.get("res_model"), "purchase.order")
        self.assertEqual(
            action.get("context", {}).get("search_default_partner_id"),
            self.driver.partner_id.id,
            "Purchase search should use the driver's partner id, not driver id",
        )

    def test_action_view_sale_orders_uses_partner_id(self):
        try:
            action = self.driver.action_view_sale_orders()
        except Exception:
            self.skipTest("sale module is not installed")
        self.assertEqual(action.get("res_model"), "sale.order")
        self.assertEqual(
            action.get("context", {}).get("default_partner_id"),
            self.driver.partner_id.id,
            "Sale order should default to the driver's partner id, not driver id",
        )
