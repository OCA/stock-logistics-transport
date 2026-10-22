# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.tools.float_utils import float_round


class HrExpense(models.Model):
    _inherit = "hr.expense"

    trip_id = fields.Many2one("tms.order")
    vehicle_id = fields.Many2one("fleet.vehicle", string="Vehicle", index=True)
    odometer_id = fields.Many2one(
        "fleet.vehicle.odometer",
        string="Odometer reading",
        copy=False,
        index=True,
    )
    odometer = fields.Float(
        compute="_compute_odometer",
        inverse="_inverse_odometer",
        help="Pump reading, stored on the vehicle odometer log.",
    )
    spread_by_distance = fields.Boolean(
        related="product_id.tms_spread_by_distance",
    )
    allocation_ids = fields.One2many("tms.expense.allocation", "expense_id")
    unallocated_amount = fields.Monetary(
        string="Not allocated",
        currency_field="currency_id",
        compute="_compute_unallocated_amount",
        help="Part of this fill that no trip distance covers.",
    )

    def action_view_order(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "tms.order",
            "view_mode": "form",
            "res_id": self.trip_id.id,
            "target": "current",
            "name": self.env._("Trip: %s", self.trip_id.name),
        }

    @api.depends("odometer_id.value")
    def _compute_odometer(self):
        for expense in self:
            expense.odometer = expense.odometer_id.value

    def _inverse_odometer(self):
        for expense in self:
            expense._assign_odometer_reading(expense.odometer)

    @api.onchange("trip_id")
    def _onchange_trip_id_vehicle(self):
        if self.trip_id.vehicle_id and not self.vehicle_id:
            self.vehicle_id = self.trip_id.vehicle_id

    @api.depends(
        "total_amount",
        "allocation_ids.amount",
        "product_id.tms_spread_by_distance",
    )
    def _compute_unallocated_amount(self):
        for expense in self:
            if expense.product_id.tms_spread_by_distance:
                allocated = sum(expense.allocation_ids.mapped("amount"))
                expense.unallocated_amount = expense.total_amount - allocated
            else:
                expense.unallocated_amount = 0.0

    def _assign_odometer_reading(self, value):
        self.ensure_one()
        vehicle = self.vehicle_id or self.trip_id.vehicle_id
        if not vehicle:
            return
        if vehicle != self.vehicle_id:
            self.vehicle_id = vehicle
        reading = self.odometer_id
        vals = {
            "value": value,
            "date": fields.Date.context_today(self),
            "vehicle_id": vehicle.id,
        }
        if reading and reading.vehicle_id == vehicle:
            reading.write(vals)
            return
        self.odometer_id = self.env["fleet.vehicle.odometer"].create(vals)

    def _money_round(self, amount):
        self.ensure_one()
        currency = self.currency_id or self.company_id.currency_id
        if currency:
            return currency.round(amount)
        return float_round(amount, precision_digits=2)

    def _previous_fill(self):
        self.ensure_one()
        if not self.vehicle_id or not self.odometer_id:
            return self.env["hr.expense"]
        candidates = self.search(
            [
                ("id", "!=", self.id),
                ("vehicle_id", "=", self.vehicle_id.id),
                ("product_id.tms_spread_by_distance", "=", True),
                ("odometer_id", "!=", False),
            ]
        )
        earlier = candidates.filtered(
            lambda item: item.odometer_id.value < self.odometer_id.value
        )
        return earlier.sorted(key=lambda item: (item.odometer, item.id))[-1:]

    def _trips_in_span(self, start_value, end_value):
        self.ensure_one()
        trips = self.env["tms.order"].search(
            [
                ("vehicle_id", "=", self.vehicle_id.id),
                ("odometer_start_id", "!=", False),
                ("odometer_end_id", "!=", False),
            ]
        )
        return trips.filtered(
            lambda trip: (
                trip.odometer_start >= start_value
                and trip.odometer_end <= end_value
                and trip.odometer_end > trip.odometer_start
            )
        )

    def _rebuild_fuel_allocations(self):
        allocation_model = self.env["tms.expense.allocation"].sudo()
        for expense in self:
            allocation_model.search([("expense_id", "=", expense.id)]).unlink()
            if not expense.product_id.tms_spread_by_distance:
                continue
            if not expense.vehicle_id or not expense.odometer_id:
                continue
            if not expense.total_amount:
                continue
            previous = expense._previous_fill()
            if not previous:
                continue
            start_value = previous.odometer
            end_value = expense.odometer
            span = end_value - start_value
            if span <= 0:
                continue
            covered = expense._trips_in_span(start_value, end_value).sorted(
                key=lambda trip: (trip.odometer_start, trip.id)
            )
            shares = []
            allocated = 0.0
            for trip in covered:
                distance = trip.odometer_end - trip.odometer_start
                amount = expense._money_round(expense.total_amount * distance / span)
                shares.append((trip, distance, amount))
                allocated += amount
            if not shares:
                continue
            covered_distance = sum(distance for _trip, distance, _amount in shares)
            target = expense._money_round(
                expense.total_amount * covered_distance / span
            )
            last_trip, last_distance, last_amount = shares[-1]
            shares[-1] = (
                last_trip,
                last_distance,
                last_amount + expense._money_round(target - allocated),
            )
            for trip, distance, amount in shares:
                allocation_model.create(
                    {
                        "expense_id": expense.id,
                        "trip_id": trip.id,
                        "distance": distance,
                        "amount": amount,
                    }
                )
        self._apply_fuel_analytic_distribution()

    def _apply_fuel_analytic_distribution(self):
        """Hook for tms_account. Allocation itself does not post analytics."""
        return True

    def _fill_vehicle_from_trip(self, vals):
        if vals.get("trip_id") and not vals.get("vehicle_id"):
            trip = self.env["tms.order"].browse(vals["trip_id"])
            if trip.vehicle_id:
                vals["vehicle_id"] = trip.vehicle_id.id
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [self._fill_vehicle_from_trip(vals) for vals in vals_list]
        records = super().create(vals_list)
        if not self.env.context.get("tms_reallocating_fuel"):
            records.mapped("vehicle_id")._reallocate_fuel_expenses(
                extra=records.filtered("spread_by_distance")
            )
        return records

    def write(self, vals):
        if len(self) == 1:
            self._fill_vehicle_from_trip(vals)
        vehicles = self.mapped("vehicle_id")
        result = super().write(vals)
        watched = {
            "vehicle_id",
            "odometer",
            "odometer_id",
            "total_amount",
            "total_amount_currency",
            "quantity",
            "price_unit",
            "product_id",
            "trip_id",
        }
        if not self.env.context.get("tms_reallocating_fuel") and watched & set(vals):
            (vehicles | self.mapped("vehicle_id"))._reallocate_fuel_expenses(extra=self)
        return result

    def unlink(self):
        vehicles = self.mapped("vehicle_id")
        result = super().unlink()
        if not self.env.context.get("tms_reallocating_fuel"):
            vehicles._reallocate_fuel_expenses()
        return result
