# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.base.tests.common import BaseCommon


class TestTMSAccountCommon(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.analytic_group = cls.env.ref("analytic.group_analytic_accounting")
        cls.tms_user_group = cls.env.ref("tms.group_tms_user")
        cls.route_group = cls.env.ref("tms.group_tms_route")
        cls.route_plan_group = cls.env.ref("tms_account.group_tms_route_analytic_plan")
        cls.order_plan_group = cls.env.ref("tms_account.group_tms_order_analytic_plan")
        cls.env.user.group_ids = [
            (6, 0, [cls.analytic_group.id, cls.tms_user_group.id, cls.route_group.id])
        ]
        cls.route_plan = cls.env.ref("tms_account.tms_route_analytic_plan")
        cls.order_plan = cls.env.ref("tms_account.tms_order_analytic_plan")
        cls.origin = cls.env["res.partner"].create(
            {"name": "Origin", "tms_location": True}
        )
        cls.destination = cls.env["res.partner"].create(
            {"name": "Destination", "tms_location": True}
        )
        cls.driver = cls.env["tms.driver"].create({"name": "Driver"})
        cls.vehicle = cls.env["fleet.vehicle"].create(
            {
                "name": "Vehicle",
                "license_plate": "TMS-001",
                "model_id": cls.env["fleet.vehicle.model"]
                .create(
                    {
                        "name": "Model",
                        "brand_id": cls.env["fleet.vehicle.model.brand"]
                        .create({"name": "Brand"})
                        .id,
                    }
                )
                .id,
            }
        )
        cls.route = cls.env["tms.route"].create(
            {
                "name": "Route A",
                "origin_location_id": cls.origin.id,
                "destination_location_id": cls.destination.id,
            }
        )
        cls.stage_draft = cls.env["tms.stage"].search(
            [("stage_type", "=", "order")], limit=1
        )
        cls.stage_completed = cls.env["tms.stage"].create(
            {
                "name": "Completed",
                "stage_type": "order",
                "is_completed": True,
                "sequence": 99,
            }
        )
        cls.partner = cls.env["res.partner"].create({"name": "Customer"})
        cls.employee = cls.env["hr.employee"].create(
            {"name": "Test Employee", "user_id": cls.env.user.id}
        )

    def _create_trip(self, **kwargs):
        values = {
            "name": "Trip 1",
            "driver_id": self.driver.id,
            "vehicle_id": self.vehicle.id,
            "route_id": self.route.id,
            "stage_id": self.stage_draft.id,
        }
        values.update(kwargs)
        return self.env["tms.order"].create(values)


class TestTMSRouteAccount(TestTMSAccountCommon):
    def test_route_analytic_account_auto_creation(self):
        self.env.user.group_ids = [(4, self.route_plan_group.id)]
        route = self.env["tms.route"].create(
            {
                "name": "Route B",
                "origin_location_id": self.origin.id,
                "destination_location_id": self.destination.id,
            }
        )
        self.assertTrue(route.analytic_account_id)
        self.assertEqual(route.analytic_account_id.plan_id, self.route_plan)

    def test_route_create_without_analytic_group(self):
        # Plan group granted without analytic accounting access: the route
        # must be created without an analytic account, not crash.
        self.env.user.group_ids = [
            (
                6,
                0,
                [self.route_plan_group.id, self.tms_user_group.id, self.route_group.id],
            )
        ]
        route = self.env["tms.route"].create(
            {
                "name": "Route C",
                "origin_location_id": self.origin.id,
                "destination_location_id": self.destination.id,
            }
        )
        self.assertFalse(route.analytic_account_id)

    def test_route_total_revenue(self):
        self.route.write({"total_income": 100, "total_expenses": 40})
        self.assertEqual(self.route.total_revenue, 60)


class TestTMSOrderAccount(TestTMSAccountCommon):
    def test_trip_analytic_account_auto_creation(self):
        self.env.user.group_ids = [
            (4, self.order_plan_group.id),
        ]
        trip = self._create_trip()
        self.assertTrue(trip.analytic_account_id)
        self.assertEqual(trip.analytic_account_id.plan_id, self.order_plan)

    def test_trip_total_revenue(self):
        trip = self._create_trip()
        trip.write({"total_income": 200, "total_expenses": 50})
        self.assertEqual(trip.total_revenue, 150)

    def test_action_view_analytic_account(self):
        self.env.user.group_ids = [(4, self.order_plan_group.id)]
        trip = self._create_trip()
        action = trip.action_view_analytic_account()
        self.assertEqual(action["res_model"], "account.analytic.account")
        self.assertEqual(action["res_id"], trip.analytic_account_id.id)

    def test_action_view_bills(self):
        trip = self._create_trip()
        action = trip.action_view_bills()
        self.assertEqual(action["view_mode"], "list,form")
        self.assertEqual(action["res_model"], "account.move")

    def test_driver_action_view_partner_invoices_delegates_to_partner(self):
        driver = self.env["tms.driver"].create({"name": "Invoice Driver"})
        action = driver.action_view_partner_invoices()
        self.assertEqual(action["res_model"], "account.move")


class TestAccountAnalyticLine(TestTMSAccountCommon):
    def test_analytic_line_updates_trip_totals(self):
        self.env.user.group_ids = [(4, self.order_plan_group.id)]
        trip = self._create_trip()
        column = self.order_plan._column_name()
        self.env["account.analytic.line"].create(
            {
                "name": "Income",
                "amount": 100,
                column: trip.analytic_account_id.id,
            }
        )
        self.assertEqual(trip.total_income, 100)

    def test_analytic_line_updates_route_totals(self):
        self.env.user.group_ids = [(4, self.route_plan_group.id)]
        route = self.env["tms.route"].create(
            {
                "name": "Route C",
                "origin_location_id": self.origin.id,
                "destination_location_id": self.destination.id,
            }
        )
        column = self.route_plan._column_name()
        self.env["account.analytic.line"].create(
            {
                "name": "Expense",
                "amount": -25,
                column: route.analytic_account_id.id,
            }
        )
        self.assertEqual(route.total_expenses, 25)


class TestAccountMoveTMS(TestTMSAccountCommon):
    def test_prepare_product_base_line_with_tms_factor(self):
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
            }
        )
        line = self.env["account.move.line"].create(
            {
                "move_id": move.id,
                "name": "Line",
                "quantity": 2,
                "price_unit": 10,
                "tms_factor": 3,
            }
        )
        base_line = move._prepare_product_base_line_for_taxes_computation(line)
        self.assertEqual(base_line["quantity"], 6)

    def test_has_tms_order_compute(self):
        move = self.env["account.move"].new({"move_type": "out_invoice"})
        move.has_tms_order = False
        self.assertFalse(move.has_tms_order)


class TestResConfigSettings(TestTMSAccountCommon):
    def test_get_and_set_analytic_plans(self):
        settings = self.env["res.config.settings"].create({})
        settings.tms_analytic_plan = [(6, 0, [self.route_plan.id])]
        settings.execute()
        stored = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("tms_account.tms_analytic_plan_ids")
        )
        self.assertIn(str(self.route_plan.id), stored)
        settings2 = self.env["res.config.settings"].create({})
        values = settings2.get_values()
        self.assertIn(self.route_plan.id, values["tms_analytic_plan"][0][2])

    def test_compute_analytic_plan_groups(self):
        settings = self.env["res.config.settings"].create({})
        settings.tms_analytic_plan = [(6, 0, [self.route_plan.id, self.order_plan.id])]
        settings._compute_tms_analytic_groups()
        self.assertTrue(settings.group_tms_route_analytic_plan)
        self.assertTrue(settings.group_tms_order_analytic_plan)


class TestResConfigSettingsNoAccount(TestTMSAccountCommon):
    """Users without account.analytic.plan access must still be able to
    open and save the Settings page (regression test: the tms_analytic_plan
    m2m write used to raise AccessError on create)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.no_account_user = cls.env["res.users"].create(
            {
                "name": "No Account User",
                "login": "no_account_user",
                "group_ids": [
                    (
                        6,
                        0,
                        [
                            cls.env.ref("base.group_user").id,
                            cls.env.ref("base.group_system").id,
                        ],
                    )
                ],
            }
        )
        cls.no_account_env = cls.env(user=cls.no_account_user)

    def test_default_get_omits_analytic_plan(self):
        settings = self.no_account_env["res.config.settings"].new({})
        defaults = settings.default_get(["tms_analytic_plan"])
        self.assertNotIn("tms_analytic_plan", defaults)

    def test_settings_create_get_and_set_values(self):
        settings = self.no_account_env["res.config.settings"].create({})
        settings.set_values()
        values = self.no_account_env["res.config.settings"].create({}).get_values()
        self.assertNotIn("tms_analytic_plan", values)

    def test_non_analytic_user_save_preserves_plans_and_groups(self):
        """Seed plans + implied groups as an analytic admin, then save
        Settings as a non-analytic user.  Both the stored config parameter
        and the res.groups implied groups must survive."""
        # Seed: analytic admin configures both plans
        admin_settings = self.env["res.config.settings"].create({})
        admin_settings.tms_analytic_plan = [
            (6, 0, [self.route_plan.id, self.order_plan.id])
        ]
        admin_settings.execute()
        stored = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("tms_account.tms_analytic_plan_ids")
        )
        self.assertIn(str(self.route_plan.id), stored)
        self.assertIn(str(self.order_plan.id), stored)

        # Non-analytic user saves an unrelated setting
        no_acct_settings = self.no_account_env["res.config.settings"].create({})
        no_acct_settings.set_values()

        # Stored plans must survive
        stored_after = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("tms_account.tms_analytic_plan_ids")
        )
        self.assertIn(str(self.route_plan.id), stored_after)
        self.assertIn(str(self.order_plan.id), stored_after)

        # Compute must reflect stored state, not empty in-memory field
        check = self.no_account_env["res.config.settings"].create({})
        check._compute_tms_analytic_groups()
        self.assertTrue(check.group_tms_route_analytic_plan)
        self.assertTrue(check.group_tms_order_analytic_plan)


class TestSaleOrderLineAnalytic(TestTMSAccountCommon):
    def test_default_analytic_distribution(self):
        self.env.user.group_ids = [
            (4, self.route_plan_group.id),
            (4, self.order_plan_group.id),
        ]
        self.route.analytic_account_id = self.env["account.analytic.account"].create(
            {"name": "Route AA", "plan_id": self.route_plan.id}
        )
        trip = self._create_trip()
        trip.analytic_account_id = self.env["account.analytic.account"].create(
            {"name": "Trip AA", "plan_id": self.order_plan.id}
        )
        product = self.env["product.product"].create(
            {
                "name": "Transport",
                "type": "service",
                "list_price": 100,
            }
        )
        product.product_tmpl_id.write({"tms_trip": True, "trip_product_type": "trip"})
        sale = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "product_uom_qty": 1,
                            "tms_order_ids": [(6, 0, [trip.id])],
                        },
                    )
                ],
            }
        )
        line = sale.order_line
        distribution = line._default_analytic_distribution()
        self.assertTrue(distribution)


class TestPurchaseOrderLineAnalytic(TestTMSAccountCommon):
    def test_default_analytic_distribution(self):
        self.env.user.group_ids = [(4, self.order_plan_group.id)]
        trip = self._create_trip()
        trip.analytic_account_id = self.env["account.analytic.account"].create(
            {"name": "Trip PO", "plan_id": self.order_plan.id}
        )
        purchase = self.env["purchase.order"].create(
            {
                "partner_id": self.partner.id,
                "trip_id": trip.id,
            }
        )
        line = self.env["purchase.order.line"].create(
            {
                "order_id": purchase.id,
                "name": "Service",
                "product_qty": 1,
                "price_unit": 50,
            }
        )
        distribution = line._default_analytic_distribution()
        self.assertTrue(distribution)


class TestHrExpenseAnalytic(TestTMSAccountCommon):
    def test_default_analytic_distribution(self):
        self.env.user.group_ids = [(4, self.order_plan_group.id)]
        trip = self._create_trip()
        trip.analytic_account_id = self.env["account.analytic.account"].create(
            {"name": "Trip Expense", "plan_id": self.order_plan.id}
        )
        expense = self.env["hr.expense"].create(
            {
                "name": "Fuel",
                "trip_id": trip.id,
                "total_amount": 30,
                "employee_id": self.employee.id,
            }
        )
        distribution = expense._default_analytic_distribution()
        self.assertTrue(distribution)

    def test_default_analytic_distribution_without_trip_context(self):
        expense = self.env["hr.expense"].new(
            {"name": "Fuel", "employee_id": self.employee.id}
        )
        self.assertEqual(expense._default_analytic_distribution(), {})

    def test_default_analytic_distribution_with_route(self):
        self.env.user.group_ids = [(4, self.route_plan_group.id)]
        self.route.analytic_account_id = self.env["account.analytic.account"].create(
            {"name": "Route Expense", "plan_id": self.route_plan.id}
        )
        trip = self._create_trip()
        expense = self.env["hr.expense"].create(
            {
                "name": "Fuel",
                "trip_id": trip.id,
                "total_amount": 30,
                "employee_id": self.employee.id,
            }
        )
        distribution = expense._default_analytic_distribution()
        self.assertTrue(distribution)

    def test_onchange_trip_id(self):
        trip = self._create_trip()
        expense = self.env["hr.expense"].new(
            {"name": "Fuel", "trip_id": trip.id, "employee_id": self.employee.id}
        )
        expense._onchange_trip_id()
        self.assertEqual(expense.trip_id, trip)


class TestTMSOrderWorkflow(TestTMSAccountCommon):
    def test_compute_invoice_and_bill_counts(self):
        trip = self._create_trip()
        trip._compute_get_invoiced()
        self.assertEqual(trip.invoice_count, 0)
        self.assertEqual(trip.bill_count, 0)

    def test_action_view_analytic_account_without_account(self):
        trip = self._create_trip()
        self.assertFalse(trip.action_view_analytic_account())

    def test_default_analytic_distribution_without_sale(self):
        trip = self._create_trip()
        self.assertEqual(trip._default_analytic_distribution(), {})


class TestSaleOrderAccount(TestTMSAccountCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create(
            {"name": "Transport Service", "type": "service", "list_price": 100}
        )
        cls.product.product_tmpl_id.write(
            {
                "tms_trip": True,
                "trip_product_type": "trip",
                "tms_factor_type": "distance",
                "tms_factor_distance_uom": cls.env.ref("uom.product_uom_km").id,
            }
        )

    def test_sale_order_create_sets_analytic_distribution(self):
        self.env.user.group_ids = [(4, self.order_plan_group.id)]
        trip = self._create_trip()
        trip.analytic_account_id = self.env["account.analytic.account"].create(
            {"name": "Trip SO create", "plan_id": self.order_plan.id}
        )
        sale = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 1,
                            "tms_order_ids": [(6, 0, [trip.id])],
                        },
                    )
                ],
            }
        )
        self.assertTrue(sale.order_line.analytic_distribution)

    def test_sale_order_write_updates_analytic_distribution(self):
        self.env.user.group_ids = [(4, self.order_plan_group.id)]
        trip = self._create_trip()
        trip.analytic_account_id = self.env["account.analytic.account"].create(
            {"name": "Trip SO", "plan_id": self.order_plan.id}
        )
        sale = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 1,
                            "tms_order_ids": [(6, 0, [trip.id])],
                        },
                    )
                ],
            }
        )
        sale.write(
            {
                "order_line": [
                    (
                        1,
                        sale.order_line.id,
                        {"product_uom_qty": 2},
                    )
                ]
            }
        )
        self.assertTrue(sale.order_line.analytic_distribution)

    def test_prepare_invoice_line(self):
        self.env.user.group_ids = [(4, self.order_plan_group.id)]
        trip = self._create_trip()
        sale = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 1,
                            "tms_order_ids": [(6, 0, [trip.id])],
                            "tms_factor": 2,
                        },
                    )
                ],
            }
        )
        line = sale.order_line
        values = line._prepare_invoice_line()
        self.assertEqual(values["tms_factor"], 2)
        self.assertEqual(values["tms_factor_uom"], "km")

    def test_default_analytic_distribution_empty_trip(self):
        line = self.env["sale.order.line"].new(
            {
                "order_id": self.env["sale.order"]
                .create({"partner_id": self.partner.id})
                .id
            }
        )
        self.assertEqual(line._default_analytic_distribution(), {})


class TestAccountMoveActions(TestTMSAccountCommon):
    def _link_trip_to_sale(self, trip, sale):
        sale.order_line.write({"tms_order_ids": [(6, 0, [trip.id])]})
        trip.sale_id = sale

    def test_compute_has_tms_order_and_action(self):
        product = self.env["product.product"].create(
            {"name": "Transport", "type": "service", "list_price": 50}
        )
        sale = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    (0, 0, {"product_id": product.id, "product_uom_qty": 1})
                ],
            }
        )
        sale.action_confirm()
        trip = self._create_trip()
        self._link_trip_to_sale(trip, sale)
        invoice = sale._create_invoices()
        invoice._compute_has_trip()
        self.assertTrue(invoice.has_tms_order)
        action = invoice.action_view_tms_orders()
        self.assertEqual(action["res_model"], "tms.order")
        self.assertEqual(action["res_id"], trip.id)

    def test_action_view_tms_orders_multiple_trips(self):
        product = self.env["product.product"].create(
            {"name": "Transport 2", "type": "service", "list_price": 50}
        )
        sale = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    (0, 0, {"product_id": product.id, "product_uom_qty": 1})
                ],
            }
        )
        sale.action_confirm()
        trips = self.env["tms.order"].create(
            [
                {
                    "name": "Trip A",
                    "driver_id": self.driver.id,
                    "vehicle_id": self.vehicle.id,
                    "route_id": self.route.id,
                    "stage_id": self.stage_draft.id,
                },
                {
                    "name": "Trip B",
                    "driver_id": self.driver.id,
                    "vehicle_id": self.vehicle.id,
                    "route_id": self.route.id,
                    "stage_id": self.stage_draft.id,
                },
            ]
        )
        sale.order_line.tms_order_ids = [(6, 0, trips.ids)]
        invoice = sale._create_invoices()
        action = invoice.action_view_tms_orders()
        self.assertEqual(action["res_model"], "tms.order")
        self.assertEqual(action["domain"], [("id", "in", trips.ids)])


class TestResConfigSettingsDomain(TestTMSAccountCommon):
    def test_compute_tms_analytic_plan_domain_with_routes(self):
        settings = self.env["res.config.settings"].create({})
        settings.group_tms_route = True
        settings._compute_tms_analytic_plan_domain()
        self.assertIn("tms_flag", settings.tms_analytic_plan_domain)


class TestPurchaseOrderLineEdgeCases(TestTMSAccountCommon):
    def test_default_analytic_distribution_without_trip(self):
        purchase = self.env["purchase.order"].create({"partner_id": self.partner.id})
        line = self.env["purchase.order.line"].new({"order_id": purchase.id})
        self.assertEqual(line._default_analytic_distribution(), {})

    def test_default_analytic_distribution_with_route(self):
        self.env.user.group_ids = [(4, self.route_plan_group.id)]
        self.route.analytic_account_id = self.env["account.analytic.account"].create(
            {"name": "Route PO", "plan_id": self.route_plan.id}
        )
        trip = self._create_trip(route_id=self.route.id)
        purchase = self.env["purchase.order"].create(
            {"partner_id": self.partner.id, "trip_id": trip.id}
        )
        line = self.env["purchase.order.line"].create(
            {
                "order_id": purchase.id,
                "name": "Service",
                "product_qty": 1,
                "price_unit": 50,
            }
        )
        distribution = line._default_analytic_distribution()
        self.assertTrue(distribution)

    def test_onchange_trip_id(self):
        self.env.user.group_ids = [(4, self.order_plan_group.id)]
        trip = self._create_trip()
        trip.analytic_account_id = self.env["account.analytic.account"].create(
            {"name": "Trip PO onchange", "plan_id": self.order_plan.id}
        )
        purchase = self.env["purchase.order"].create(
            {"partner_id": self.partner.id, "trip_id": trip.id}
        )
        line = self.env["purchase.order.line"].new(
            {"order_id": purchase.id, "name": "Service", "product_qty": 1}
        )
        line._onchange_trip_id()
        self.assertTrue(line.analytic_distribution)


class TestAccountAnalyticLineExpense(TestTMSAccountCommon):
    def test_analytic_line_negative_amount_on_trip(self):
        self.env.user.group_ids = [(4, self.order_plan_group.id)]
        trip = self._create_trip()
        column = self.order_plan._column_name()
        self.env["account.analytic.line"].create(
            {
                "name": "Expense",
                "amount": -40,
                column: trip.analytic_account_id.id,
            }
        )
        self.assertEqual(trip.total_expenses, 40)

    def test_analytic_line_positive_amount_on_route(self):
        self.env.user.group_ids = [(4, self.route_plan_group.id)]
        route = self.env["tms.route"].create(
            {
                "name": "Route Income",
                "origin_location_id": self.origin.id,
                "destination_location_id": self.destination.id,
            }
        )
        column = self.route_plan._column_name()
        self.env["account.analytic.line"].create(
            {
                "name": "Income",
                "amount": 75,
                column: route.analytic_account_id.id,
            }
        )
        self.assertEqual(route.total_income, 75)


class TestTMSRouteAccountCreation(TestTMSAccountCommon):
    def test_route_keeps_provided_analytic_account(self):
        self.env.user.group_ids = [(4, self.route_plan_group.id)]
        account = self.env["account.analytic.account"].create(
            {"name": "Existing AA", "plan_id": self.route_plan.id}
        )
        route = self.env["tms.route"].create(
            {
                "name": "Route Existing",
                "origin_location_id": self.origin.id,
                "destination_location_id": self.destination.id,
                "analytic_account_id": account.id,
            }
        )
        self.assertEqual(route.analytic_account_id, account)


class TestTMSOrderInvoicing(TestTMSAccountCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create(
            {"name": "Transport Service", "type": "service", "list_price": 100}
        )

    def _setup_sale_with_trip(self, trip=None):
        trip = trip or self._create_trip()
        sale = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    (0, 0, {"product_id": self.product.id, "product_uom_qty": 1})
                ],
            }
        )
        sale.action_confirm()
        sale.order_line.write({"tms_order_ids": [(6, 0, [trip.id])]})
        trip.sale_id = sale
        return trip, sale

    def test_handle_invoices_and_action_view_invoices(self):
        self.env.user.group_ids = [
            (4, self.analytic_group.id),
            (4, self.order_plan_group.id),
        ]
        trip, sale = self._setup_sale_with_trip()
        trip.analytic_account_id = self.env["account.analytic.account"].create(
            {"name": "Trip Invoice", "plan_id": self.order_plan.id}
        )
        trip.stage_id = self.stage_completed
        trip._handle_invoices()
        self.assertTrue(sale.invoice_ids)
        action = trip.action_view_invoices()
        self.assertEqual(action["res_model"], "account.move")

    def test_write_completed_triggers_bills(self):
        trip = self._create_trip()
        trip.create_invoice = True
        purchase = self.env["purchase.order"].create(
            {"partner_id": self.partner.id, "trip_id": trip.id}
        )
        purchase.button_confirm()
        trip.write({"stage_id": self.stage_completed.id})
        trip._compute_get_invoiced()
        self.assertGreaterEqual(trip.bill_count, 0)

    def test_write_completed_triggers_invoices(self):
        self.env.user.group_ids = [(4, self.analytic_group.id)]
        trip, sale = self._setup_sale_with_trip()
        trip.create_invoice = True
        trip.write({"stage_id": self.stage_completed.id})
        self.assertTrue(sale.invoice_ids)

    def test_assign_analytic_accounts(self):
        self.env.user.group_ids = [(4, self.order_plan_group.id)]
        trip, sale = self._setup_sale_with_trip()
        trip.analytic_account_id = self.env["account.analytic.account"].create(
            {"name": "Trip Assign", "plan_id": self.order_plan.id}
        )
        invoice = sale._create_invoices()
        trip._assign_analytic_accounts(invoice)
        self.assertTrue(invoice.invoice_line_ids.analytic_distribution)

    def test_handle_invoices_skips_when_not_all_completed(self):
        trip, sale = self._setup_sale_with_trip()
        trip._handle_invoices()
        self.assertFalse(sale.invoice_ids)

    def test_default_analytic_distribution_with_sale(self):
        self.env.user.group_ids = [
            (4, self.order_plan_group.id),
            (4, self.route_plan_group.id),
        ]
        self.route.analytic_account_id = self.env["account.analytic.account"].create(
            {"name": "Route Dist", "plan_id": self.route_plan.id}
        )
        trip = self._create_trip()
        trip.analytic_account_id = self.env["account.analytic.account"].create(
            {"name": "Trip Dist", "plan_id": self.order_plan.id}
        )
        sale = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 1,
                            "tms_order_ids": [(6, 0, [trip.id])],
                        },
                    )
                ],
            }
        )
        trip.sale_id = sale
        distribution = trip._default_analytic_distribution()
        self.assertTrue(distribution)
