# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestFuelAllocation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.origin = cls.env["res.partner"].create(
            {"name": "Fuel Origin", "tms_location": True}
        )
        cls.destination = cls.env["res.partner"].create(
            {"name": "Fuel Destination", "tms_location": True}
        )
        brand = cls.env["fleet.vehicle.model.brand"].create({"name": "Fuel Brand"})
        model = cls.env["fleet.vehicle.model"].create(
            {"name": "Fuel Model", "brand_id": brand.id}
        )
        cls.vehicle = cls.env["fleet.vehicle"].create(
            {"model_id": model.id, "license_plate": "FUEL001"}
        )
        cls.other_vehicle = cls.env["fleet.vehicle"].create(
            {"model_id": model.id, "license_plate": "FUEL002"}
        )
        cls.employee = cls.env["hr.employee"].create({"name": "Fuel Driver"})
        cls.fuel = cls.env.ref("tms_expense.expense_trip_fuel")
        cls.toll = cls.env.ref("tms_expense.expense_trip_toll")

    def _trip(self, start, end, vehicle=None, name=None):
        vehicle = vehicle or self.vehicle
        trip = self.env["tms.order"].create(
            {
                "name": name or f"Fuel {start}-{end}",
                "origin_id": self.origin.id,
                "destination_id": self.destination.id,
                "vehicle_id": vehicle.id,
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

    def _fill(self, value, amount, trip, vehicle=None):
        return self.env["hr.expense"].create(
            {
                "name": f"Fill {value}",
                "employee_id": self.employee.id,
                "product_id": self.fuel.id,
                "total_amount": amount,
                "trip_id": trip.id,
                "vehicle_id": (vehicle or self.vehicle).id,
                "odometer": value,
            }
        )

    def test_fuel_is_spread_across_trips_between_fills(self):
        first = self._trip(100000, 100100, name="Fuel A")
        second = self._trip(100100, 100250, name="Fuel B")
        third = self._trip(100250, 100400, name="Fuel C")
        outside = self._trip(120000, 120480, name="Fuel outside")
        opening = self._fill(100000, 100, third)
        closing = self._fill(100400, 400, third)
        self.assertFalse(opening.allocation_ids)
        self.assertEqual(opening.unallocated_amount, 100)
        amounts = {line.trip_id: line.amount for line in closing.allocation_ids}
        self.assertEqual(amounts[first], 100)
        self.assertEqual(amounts[second], 150)
        self.assertEqual(amounts[third], 150)
        self.assertNotIn(outside, amounts)
        self.assertEqual(closing.unallocated_amount, 0)
        self.assertEqual(first.fuel_allocated, 100)
        self.assertEqual(second.fuel_allocated, 150)
        self.assertEqual(third.fuel_allocated, 150)
        self.assertEqual(closing.odometer_id.vehicle_id, self.vehicle)
        self.assertEqual(closing.odometer_id.value, 100400)

    def test_toll_stays_on_the_trip_that_recorded_it(self):
        trip = self._trip(5000, 5100, name="Toll trip")
        trip.trip_pay = 300
        toll = self.env["hr.expense"].create(
            {
                "name": "Toll booth",
                "employee_id": self.employee.id,
                "product_id": self.toll.id,
                "total_amount": 40,
                "trip_id": trip.id,
                "vehicle_id": self.vehicle.id,
                "odometer": 5100,
            }
        )
        self.assertFalse(toll.allocation_ids)
        self.assertEqual(toll.unallocated_amount, 0)
        self.assertEqual(trip.expense_total, 40)
        self.assertEqual(trip.settlement_balance, 260)
        self.assertEqual(trip.fuel_allocated, 0)

    def test_settlement_keeps_the_full_fuel_receipt(self):
        self._trip(1000, 1100, name="Settle A")
        self._trip(1100, 1300, name="Settle B")
        paid_on = self._trip(1300, 1400, name="Settle C")
        paid_on.trip_pay = 1000
        self._fill(1000, 50, paid_on)
        closing = self._fill(1400, 400, paid_on)
        self.assertEqual(paid_on.expense_total, 450)
        self.assertEqual(paid_on.settlement_balance, 550)
        self.assertEqual(paid_on.fuel_allocated, 100)
        share = closing.allocation_ids.filtered(lambda line: line.trip_id == paid_on)
        self.assertEqual(share.amount, 100)

    def test_uncovered_distance_stays_on_the_fill(self):
        trip = self._trip(2000, 2100, name="Partial")
        self._fill(2000, 10, trip)
        closing = self._fill(2400, 400, trip)
        self.assertEqual(len(closing.allocation_ids), 1)
        self.assertEqual(closing.allocation_ids.amount, 100)
        self.assertEqual(closing.allocation_ids.distance, 100)
        self.assertEqual(closing.unallocated_amount, 300)
        self.assertEqual(trip.fuel_allocated, 100)

    def test_a_trip_without_an_arrival_reading_is_left_out(self):
        started = self._trip(3000, 3100, name="Open arrival")
        started.write({"odometer_end_id": False})
        closed = self._trip(3100, 3200, name="Closed arrival")
        self._fill(3000, 10, closed)
        closing = self._fill(3200, 200, closed)
        self.assertEqual(closing.allocation_ids.trip_id, closed)
        self.assertEqual(closing.allocation_ids.amount, 100)
        self.assertEqual(started.fuel_allocated, 0)
        self.assertEqual(closing.unallocated_amount, 100)

    def test_inserting_a_fill_resplits_the_following_one(self):
        first = self._trip(4000, 4200, name="Insert A")
        second = self._trip(4200, 4400, name="Insert B")
        self._fill(4000, 10, first)
        closing = self._fill(4400, 400, second)
        self.assertEqual(sum(closing.allocation_ids.mapped("amount")), 400)
        middle = self._fill(4200, 200, first)
        closing.invalidate_recordset(["allocation_ids"])
        self.assertEqual(sum(middle.allocation_ids.mapped("distance")), 200)
        self.assertEqual(middle.allocation_ids.amount, 200)
        self.assertEqual(closing.allocation_ids.trip_id, second)
        self.assertEqual(closing.allocation_ids.distance, 200)
        self.assertEqual(closing.allocation_ids.amount, 400)

    def test_rounding_remainder_lands_on_the_last_trip(self):
        trips = [
            self._trip(7000, 7001, name="Round A"),
            self._trip(7001, 7002, name="Round B"),
            self._trip(7002, 7003, name="Round C"),
        ]
        self._fill(7000, 1, trips[0])
        closing = self._fill(7003, 10, trips[2])
        by_trip = {line.trip_id: line.amount for line in closing.allocation_ids}
        self.assertAlmostEqual(by_trip[trips[0]], 3.33, places=2)
        self.assertAlmostEqual(by_trip[trips[1]], 3.33, places=2)
        self.assertAlmostEqual(by_trip[trips[2]], 3.34, places=2)
        self.assertAlmostEqual(sum(by_trip.values()), 10, places=2)
        self.assertEqual(closing.unallocated_amount, 0)

    def test_fills_of_another_vehicle_are_ignored(self):
        trip = self._trip(6000, 6100, name="Own vehicle")
        other = self._trip(6000, 6100, vehicle=self.other_vehicle, name="Other vehicle")
        self._fill(6000, 10, trip)
        self._fill(6000, 10, other, vehicle=self.other_vehicle)
        closing = self._fill(6100, 80, trip)
        self.assertEqual(closing.allocation_ids.trip_id, trip)
        self.assertEqual(closing.allocation_ids.amount, 80)
        self.assertEqual(other.fuel_allocated, 0)
