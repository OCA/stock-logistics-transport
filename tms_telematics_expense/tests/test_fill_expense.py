# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestFillExpense(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        brand = cls.env["fleet.vehicle.model.brand"].create({"name": "Fill Brand"})
        model = cls.env["fleet.vehicle.model"].create(
            {"name": "Fill Model", "brand_id": brand.id}
        )
        cls.driver = cls.env["tms.driver"].create(
            {"name": "Fill Driver", "phone": "5550001"}
        )
        cls.vehicle = cls.env["fleet.vehicle"].create(
            {
                "model_id": model.id,
                "license_plate": "FILL001",
                "vin_sn": "VIN-FILL-001",
                "odometer_unit": "kilometers",
                "tms_driver_id": cls.driver.id,
            }
        )
        cls.origin = cls.env["res.partner"].create(
            {"name": "Fill Origin", "tms_location": True}
        )
        cls.destination = cls.env["res.partner"].create(
            {"name": "Fill Destination", "tms_location": True}
        )
        cls.account = cls.env["tms.telematics.account"].create({"name": "Fill feed"})
        cls.fuel = cls.env.ref("tms_expense.expense_trip_fuel")

    def _reading(self, **extra):
        payload = {
            "external_id": "fill-1",
            "device_external_id": "dev-fill",
            "device_name": "Fill tracker",
            "event": "fill",
            "timestamp": "2026-09-10T12:00:00Z",
            "vin": "VIN-FILL-001",
            "odometer_km": 100400,
            "fuel_liters": 180,
            "fuel_cost": 4500,
        }
        payload.update(extra)
        return payload

    def _trip(self, start, end, name):
        trip = self.env["tms.order"].create(
            {
                "name": name,
                "origin_id": self.origin.id,
                "destination_id": self.destination.id,
                "vehicle_id": self.vehicle.id,
                "driver_id": self.driver.id,
            }
        )
        trip.write(
            {
                "odometer_start": start,
                "odometer_end": end,
                "distance_loaded": end - start,
            }
        )
        return trip

    def test_a_fill_creates_one_fuel_expense_on_the_vehicle(self):
        created = self.account.apply_readings([self._reading()])
        expense = created.expense_id
        self.assertEqual(created.fuel_cost, 4500)
        self.assertEqual(expense.product_id, self.fuel)
        self.assertEqual(expense.vehicle_id, self.vehicle)
        self.assertEqual(expense.quantity, 180)
        self.assertEqual(expense.total_amount_currency, 4500)
        self.assertEqual(expense.employee_id.work_contact_id, self.driver.partner_id)
        self.assertEqual(expense.odometer_id.vehicle_id, self.vehicle)
        self.assertEqual(expense.odometer_id.value, 100400)
        self.assertEqual(created.action_open_expense()["res_id"], expense.id)
        again = self.account.apply_readings([self._reading()])
        self.assertFalse(again)
        self.assertEqual(self.env["hr.expense"].search_count([]), 1)

    def test_liters_use_the_fuel_product_cost_when_no_receipt_is_sent(self):
        self.fuel.standard_price = 20
        created = self.account.apply_readings(
            [self._reading(external_id="liters", fuel_cost=False)]
        )
        self.assertEqual(created.fuel_cost, 0)
        self.assertEqual(created.expense_id.total_amount_currency, 3600)

    def test_the_second_fill_is_split_across_the_trips_in_between(self):
        first = self._trip(100000, 100100, "Fill A")
        second = self._trip(100100, 100250, "Fill B")
        third = self._trip(100250, 100400, "Fill C")
        self.account.apply_readings(
            [
                self._reading(
                    external_id="open",
                    timestamp="2026-09-01T08:00:00Z",
                    odometer_km=100000,
                    fuel_liters=40,
                    fuel_cost=100,
                ),
                self._reading(
                    external_id="close",
                    odometer_km=100400,
                    fuel_liters=80,
                    fuel_cost=400,
                ),
            ]
        )
        closing = self.env["tms.telematics.reading"].search(
            [("external_id", "=", "close")]
        )
        self.assertEqual(closing.expense_id.trip_id, third)
        amounts = {
            line.trip_id: line.amount for line in closing.expense_id.allocation_ids
        }
        self.assertEqual(amounts[first], 100)
        self.assertEqual(amounts[second], 150)
        self.assertEqual(amounts[third], 150)
        self.assertEqual(closing.expense_id.unallocated_amount, 0)

    def test_a_fill_without_a_span_uses_the_open_trip(self):
        trip = self.env["tms.order"].create(
            {
                "name": "Open fill",
                "origin_id": self.origin.id,
                "destination_id": self.destination.id,
                "vehicle_id": self.vehicle.id,
                "driver_id": self.driver.id,
            }
        )
        created = self.account.apply_readings(
            [self._reading(external_id="open-trip", odometer_km=False)]
        )
        self.assertEqual(created.expense_id.trip_id, trip)
        self.assertFalse(created.expense_id.odometer_id)
        self.assertFalse(created.expense_id.allocation_ids)

    def test_an_odometer_outside_every_trip_stays_on_the_open_trip(self):
        closed = self._trip(1000, 1100, "Elsewhere")
        closed.stage_id = self.env.ref("tms.tms_stage_order_completed")
        trip = self.env["tms.order"].create(
            {
                "name": "Still open",
                "origin_id": self.origin.id,
                "destination_id": self.destination.id,
                "vehicle_id": self.vehicle.id,
                "driver_id": self.driver.id,
            }
        )
        created = self.account.apply_readings(
            [self._reading(external_id="outside", odometer_km=50, fuel_cost=10)]
        )
        self.assertEqual(created.expense_id.trip_id, trip)

    def test_miles_are_stored_in_the_vehicle_unit(self):
        self.vehicle.odometer_unit = "miles"
        created = self.account.apply_readings(
            [self._reading(external_id="miles", odometer_km=160.9344, fuel_cost=10)]
        )
        self.assertAlmostEqual(created.expense_id.odometer, 100, places=1)

    def test_a_fill_without_quantity_or_cost_creates_nothing(self):
        created = self.account.apply_readings(
            [
                self._reading(
                    external_id="empty",
                    fuel_liters=False,
                    fuel_cost=False,
                    odometer_km=False,
                )
            ]
        )
        self.assertFalse(created.expense_id)
        self.assertFalse(created.action_open_expense())

    def test_a_fill_without_a_vehicle_creates_nothing(self):
        created = self.account.apply_readings(
            [self._reading(external_id="noveh", vin="MISSING", license_plate="NONE")]
        )
        self.assertFalse(created.device_id.vehicle_id)
        self.assertFalse(created.expense_id)

    def test_a_fill_without_a_driver_creates_nothing(self):
        self.vehicle.tms_driver_id = False
        created = self.account.apply_readings([self._reading(external_id="nodriver")])
        self.assertFalse(created.expense_id)

    def test_applying_the_hook_twice_keeps_the_same_expense(self):
        created = self.account.apply_readings([self._reading(external_id="once")])
        expense = created.expense_id
        created.account_id._apply_fill(created)
        self.assertEqual(created.expense_id, expense)
        self.assertEqual(self.env["hr.expense"].search_count([]), 1)

    def test_a_missing_fuel_product_creates_nothing(self):
        self.env["ir.model.data"].search(
            [
                ("module", "=", "tms_expense"),
                ("name", "=", "expense_trip_fuel"),
            ]
        ).unlink()
        created = self.account.apply_readings([self._reading(external_id="noproduct")])
        self.assertFalse(created.expense_id)

    def test_a_receipt_without_liters_uses_today_and_a_plain_name(self):
        created = self.account.apply_readings(
            [
                self._reading(
                    external_id="cost-only",
                    fuel_liters=False,
                    fuel_cost=25,
                    timestamp=False,
                )
            ]
        )
        self.assertEqual(created.expense_id.name, "Fuel")
        self.assertEqual(created.expense_id.quantity, 1)
        self.assertEqual(created.expense_id.total_amount_currency, 25)
        self.assertEqual(
            created.expense_id.date,
            self.account._fill_date(created),
        )

    def test_liters_without_a_price_create_an_expense_of_zero(self):
        self.fuel.standard_price = 0
        created = self.account.apply_readings(
            [self._reading(external_id="free", fuel_cost=False, fuel_liters=12)]
        )
        self.assertEqual(created.expense_id.total_amount_currency, 0)
        self.assertEqual(created.expense_id.quantity, 12)

    def test_a_missing_employee_is_created_from_the_driver(self):
        self.env["hr.employee"].search(
            [("work_contact_id", "=", self.driver.partner_id.id)]
        ).unlink()
        created = self.account.apply_readings([self._reading(external_id="rehire")])
        self.assertEqual(
            created.expense_id.employee_id.work_contact_id, self.driver.partner_id
        )

    def test_an_unmatched_odometer_is_left_empty(self):
        device = self.env["tms.telematics.device"].create(
            {
                "name": "Loose tracker",
                "account_id": self.account.id,
                "external_id": "loose",
                "vehicle_id": self.vehicle.id,
            }
        )
        reading = self.env["tms.telematics.reading"].create(
            {
                "account_id": self.account.id,
                "device_id": device.id,
                "external_id": "loose-reading",
                "event": "fill",
                "odometer_km": 5,
                "fuel_liters": 1,
            }
        )
        self.assertFalse(self.account._fill_odometer(self.vehicle, reading))

    def test_demo_import_is_skipped_without_the_demo_records(self):
        readings = self.env["tms.telematics.account"]._demo_import_fills()
        self.assertFalse(readings)

    def test_demo_import_creates_the_two_fill_expenses(self):
        device = self.env["tms.telematics.device"].create(
            {
                "name": "Demo tracker",
                "account_id": self.account.id,
                "external_id": "demo-device-1",
                "vehicle_id": self.vehicle.id,
            }
        )
        self._point_xmlid("demo_telematics_account", self.account)
        self._point_xmlid("demo_telematics_device", device)
        readings = self.env["tms.telematics.account"]._demo_import_fills()
        self.assertEqual(len(readings), 2)
        self.assertEqual(
            set(readings.mapped("expense_id.total_amount_currency")),
            {2000, 4500},
        )
        device.vehicle_id = False
        self.assertFalse(self.env["tms.telematics.account"]._demo_import_fills())

    def _point_xmlid(self, name, record):
        data = self.env["ir.model.data"].search(
            [("module", "=", "tms_telematics"), ("name", "=", name)]
        )
        if data:
            data.write({"model": record._name, "res_id": record.id})
            return
        self.env["ir.model.data"].create(
            {
                "module": "tms_telematics",
                "name": name,
                "model": record._name,
                "res_id": record.id,
            }
        )
