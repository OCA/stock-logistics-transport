# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _tms_plan_confirmed_lines(self):
        """Place each shipment when the quotation becomes a sale."""
        self.ensure_one()
        created = self.env["tms.order"]
        for line in self.order_line.filtered(lambda item: not item.display_type):
            created |= self._tms_plan_line(line)
        if created:
            self._post_tms_message(created)
        return created

    def _tms_plan_line(self, line):
        self.ensure_one()
        if self._tms_line_already_planned(line):
            return self.env["tms.order"]
        template = line.product_id.product_tmpl_id
        if template.type != "service":
            return self.env["tms.order"]
        if template.transport_type == "passenger":
            return self._tms_plan_passenger_line(line)
        if template.transport_type != "cargo":
            return self.env["tms.order"]
        booking = template.booking_type
        transit = template.transit_mode
        if booking == "full_asset" and transit == "water":
            return self._tms_assign_to_closest_trip(line, check_capacity=True)
        if booking == "full_asset":
            return self._tms_create_trip_for_line(line)
        freight = self._tms_unassigned_freight(line)
        if transit == "air" and freight and set(freight.mapped("shipment_unit")) == {
            "uld"
        }:
            return self._tms_assign_to_closest_trip(line, check_capacity=True)
        if transit == "water":
            return self._tms_assign_into_shell(line, "container")
        if transit == "air":
            return self._tms_assign_into_shell(line, "uld")
        return self._tms_assign_to_closest_trip(line, check_capacity=False)

    def _tms_line_already_planned(self, line):
        template = line.product_id.product_tmpl_id
        if template.transport_type == "passenger":
            return bool(line.tms_trip_ticket_id)
        if template.transport_type != "cargo":
            return True
        if self._tms_unassigned_freight(line):
            return False
        return bool(line.tms_order_ids or line.cargo_ids)

    def _tms_unassigned_freight(self, line):
        cargos = line.cargo_ids
        if "parent_id" in cargos._fields:
            cargos = cargos.filtered(lambda cargo: not cargo.parent_id)
        return cargos.filtered(lambda cargo: not cargo.order_id)

    def _tms_create_trip_for_line(self, line):
        vals = line._prepare_line_tms_values(line)
        trip = self.env["tms.order"].sudo().create(vals)
        freight = self._tms_unassigned_freight(line)
        if freight:
            freight.write({"order_id": trip.id})
        return trip

    def _tms_matching_trips(self, line, transport_type):
        cancelled = self.env.ref(
            "tms.tms_stage_order_cancelled", raise_if_not_found=False
        )
        domain = [("start_trip", "=", False), ("end_trip", "=", False)]
        if line.tms_origin_id:
            domain.append(("origin_id", "=", line.tms_origin_id.id))
        if line.tms_destination_id:
            domain.append(("destination_id", "=", line.tms_destination_id.id))
        if line.company_id:
            domain.append(("company_id", "in", [False, line.company_id.id]))
        trips = self.env["tms.order"].search(domain)

        def matches(trip):
            operation = trip.transport_type or trip._trip_operation()
            if operation != transport_type:
                return False
            if trip.stage_id.is_completed:
                return False
            if cancelled and trip.stage_id == cancelled:
                return False
            if (
                line.tms_route_id
                and trip.route_id
                and trip.route_id != line.tms_route_id
            ):
                return False
            if not line.tms_origin_id and not line.tms_destination_id:
                return bool(line.tms_route_id) and trip.route_id == line.tms_route_id
            return True

        matched = trips.filtered(matches)
        return matched.sorted(
            key=lambda trip: (self._tms_date_distance(trip, line), trip.id)
        )

    def _tms_date_distance(self, trip, line):
        def gap(left, right):
            if not left or not right:
                return 10**12
            return abs((left - right).total_seconds())

        return gap(
            trip.scheduled_date_start, line.tms_scheduled_date_start
        ) + gap(trip.scheduled_date_end, line.tms_scheduled_date_end)

    def _tms_trip_can_hold(self, trip, cargos):
        if not cargos:
            return True
        cargo_model = self.env["tms.cargo"]
        if trip.weight_capacity_set:
            extra = cargo_model._measure_in(
                cargos, "weight", "weight_uom_id", trip.cargo_weight_uom_id
            )
            if extra and extra > trip.remaining_weight + 0.01:
                return False
        if trip.volume_capacity_set:
            extra = cargo_model._measure_in(
                cargos, "volume", "volume_uom_id", trip.cargo_volume_uom_id
            )
            if extra and extra > trip.remaining_volume + 0.01:
                return False
        return True

    def _tms_assign_to_closest_trip(self, line, check_capacity):
        freight = self._tms_unassigned_freight(line)
        for trip in self._tms_matching_trips(line, "cargo"):
            if check_capacity and not self._tms_trip_can_hold(trip, freight):
                continue
            if freight:
                freight.write({"order_id": trip.id})
            return self.env["tms.order"]
        return self._tms_create_trip_for_line(line)

    def _tms_assign_into_shell(self, line, unit):
        freight = self._tms_unassigned_freight(line)
        for trip in self._tms_matching_trips(line, "cargo"):
            shells = trip.cargo_ids.filtered(
                lambda cargo, sale_line=line, shipment_unit=unit: (
                    cargo.shipment_unit == shipment_unit
                    and cargo.sale_line_id != sale_line
                )
            )
            for shell in shells:
                if not shell._shell_can_hold(freight):
                    continue
                if not self._tms_trip_can_hold(trip, freight):
                    continue
                if freight:
                    freight.write({"order_id": trip.id, "holding_id": shell.id})
                return self.env["tms.order"]
        trip = self._tms_create_trip_for_line(line)
        shell_vals = {
            "shipment_unit": unit,
            "order_id": trip.id,
            "quantity": 1,
        }
        if unit == "container":
            shell_vals["container_type"] = "40dry"
        else:
            shell_vals["uld_type"] = "ake"
        shell = self.env["tms.cargo"].sudo().create(shell_vals)
        if freight:
            freight.write({"order_id": trip.id, "holding_id": shell.id})
        return trip

    def _tms_plan_passenger_line(self, line):
        template = line.product_id.product_tmpl_id
        if template.booking_type == "full_asset":
            trip = self._tms_create_trip_for_line(line)
            line.tms_trip_ticket_id = trip
            return trip
        if template.transit_mode in ("air", "water"):
            return self._tms_assign_compartment(line)
        return self._tms_assign_seats(line)

    def _tms_passenger_qty(self, line):
        return max(int(line.product_uom_qty or 0), 1)

    def _tms_assign_seats(self, line):
        needed = self._tms_passenger_qty(line)
        for trip in self._tms_matching_trips(line, "passenger"):
            seats = trip.seat_ticket_ids.filtered(
                lambda seat: seat.available == "available" and not seat.sale_line_id
            )
            if len(seats) < needed:
                continue
            seats[:needed].write(
                {
                    "sale_line_id": line.id,
                    "product_id": line.product_id.id,
                    "price": line.price_unit,
                }
            )
            line.tms_trip_ticket_id = trip
            return self.env["tms.order"]
        raise UserError(
            self.env._(
                "No seat is available on a trip with this origin, "
                "destination, and dates."
            )
        )

    def _tms_compartment_used(self, compartment):
        lines = self.env["sale.order.line"].search(
            [("tms_compartment_id", "=", compartment.id)]
        )
        return sum(lines.mapped("product_uom_qty"))

    def _tms_assign_compartment(self, line):
        needed = self._tms_passenger_qty(line)
        for trip in self._tms_matching_trips(line, "passenger"):
            for compartment in trip.compartment_ids:
                free = compartment.capacity - self._tms_compartment_used(compartment)
                if free < needed:
                    continue
                line.tms_compartment_id = compartment
                line.tms_trip_ticket_id = trip
                return self.env["tms.order"]
        raise UserError(
            self.env._(
                "No compartment is available on a trip with this origin, "
                "destination, and dates."
            )
        )
