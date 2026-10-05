# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestLoadPlanner(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.kilogram = cls.env.ref("uom.product_uom_kgm")
        cls.cubic_meter = cls.env.ref("uom.product_uom_cubic_meter")
        brand = cls.env["fleet.vehicle.model.brand"].create({"name": "Planner Brand"})
        cls.model = cls.env["fleet.vehicle.model"].create(
            {
                "name": "Planner Box",
                "brand_id": brand.id,
                "vehicle_type": "truck",
                "max_weight_capacity": 1000.0,
                "max_weight_uom_id": cls.kilogram.id,
                "max_volume_capacity": 20.0,
                "max_volume_uom_id": cls.cubic_meter.id,
                "pallet_capacity": 12,
                "loading_length": 10.0,
                "loading_length_uom_id": cls.env.ref("uom.product_uom_meter").id,
            }
        )
        cls.model.max_pallet_positions = 8
        cls.layout = cls.env["tms.vehicle.model.space"].create(
            {
                "model_id": cls.model.id,
                "code": "ROW-1-LEFT",
                "zone": "front",
                "is_premium": True,
            }
        )
        cls.vehicle = cls.env["fleet.vehicle"].create(
            {
                "model_id": cls.model.id,
                "operation": "cargo",
                "license_plate": "PLAN-1",
            }
        )
        cls.space = cls.vehicle.space_ids
        cls.origin = cls.env["res.partner"].create(
            {"name": "Planner Origin", "tms_location": True}
        )
        cls.destination = cls.env["res.partner"].create(
            {"name": "Planner Destination", "tms_location": True}
        )
        cls.trip = cls.env["tms.order"].create(
            {
                "origin_id": cls.origin.id,
                "destination_id": cls.destination.id,
                "vehicle_id": cls.vehicle.id,
                "transport_type": "cargo",
            }
        )

    def _cargo(self, **extra):
        space_id = extra.pop("vehicle_space_id", None)
        values = {
            "name": "Boxes",
            "weight": 100.0,
            "weight_uom_id": self.kilogram.id,
            "volume": 1.0,
            "volume_uom_id": self.cubic_meter.id,
            "order_id": self.trip.id,
        }
        values.update(extra)
        if space_id:
            trip = self.env["tms.order"].browse(values["order_id"])
            allocation = trip.space_allocation_ids.filtered(
                lambda row, space_id=space_id: row.vehicle_space_id.id == space_id
            )[:1]
            self.assertTrue(allocation)
            values["space_allocation_id"] = allocation.id
        return self.env["tms.cargo"].create(values)

    def test_pallet_positions_reuse_the_model_field(self):
        self.assertEqual(self.model.pallet_capacity, 8)
        self.assertEqual(self.layout.model_id, self.model)
        self.assertEqual(self.space.model_space_id, self.layout)
        self.assertEqual(self.space.vehicle_id, self.vehicle)

    def test_booking_within_capacity_is_kept(self):
        cargo = self._cargo(weight=400.0, vehicle_space_id=self.space.id)
        self.assertEqual(cargo.order_id, self.trip)
        self.assertAlmostEqual(self.trip.weight_load_percent, 40.0)

    def test_booking_over_payload_is_refused(self):
        with self.assertRaises(ValidationError):
            self._cargo(weight=1500.0)

    def test_unset_payload_does_not_block(self):
        self.model.max_weight_capacity = 0.0
        cargo = self._cargo(weight=5000.0)
        self.assertEqual(cargo.order_id, self.trip)

    def test_vehicle_swap_refuses_a_smaller_model(self):
        self._cargo(weight=800.0)
        small_model = self.env["fleet.vehicle.model"].create(
            {
                "name": "Small Box",
                "brand_id": self.model.brand_id.id,
                "max_weight_capacity": 100.0,
                "max_weight_uom_id": self.kilogram.id,
            }
        )
        small = self.env["fleet.vehicle"].create(
            {
                "model_id": small_model.id,
                "operation": "cargo",
                "license_plate": "PLAN-2",
            }
        )
        with self.assertRaises(ValidationError):
            self.trip.vehicle_id = small

    def test_planner_lists_assigned_cargo_and_the_pool(self):
        assigned = self._cargo(name="On trip", weight=50.0)
        pool = self._cargo(name="Waiting", weight=20.0, order_id=False)
        data = self.trip.get_load_planner_data()
        self.assertEqual(data["length"], 10.0)
        self.assertEqual(data["vehicle_type"], "truck")
        self.assertEqual(data["spaces"][0]["code"], "ROW-1-LEFT")
        self.assertIn(assigned.id, [row["id"] for row in data["assigned"]])
        self.assertIn(pool.id, [row["id"] for row in data["pool"]])
        updated = self.trip.assign_load_planner_cargo(pool.id, self.space.id)
        self.assertEqual(pool.space_allocation_id.vehicle_space_id, self.space)
        self.assertIn(pool.id, [row["id"] for row in updated["assigned"]])
        self.assertEqual(updated["spaces"][0]["status"], "stackable")

    def test_planner_moves_cargo_to_another_space(self):
        other = self._slot("NEXT", 0.0)
        cargo = self._cargo(name="Box", weight=40.0, vehicle_space_id=self.space.id)
        data = self.trip.assign_load_planner_cargo(cargo.id, other.id)
        self.assertEqual(cargo.space_allocation_id.vehicle_space_id, other)
        booked = next(row for row in data["allocations"] if row["cargo_id"] == cargo.id)
        self.assertEqual(booked["code"], "NEXT")
        self.assertEqual(booked["state"], "booked")
        self.assertEqual(booked["cargo_name"], "Box")
        self.assertEqual(booked["weight"], 40.0)
        previous = next(
            row for row in data["allocations"] if row["code"] == "ROW-1-LEFT"
        )
        self.assertEqual(previous["state"], "available")
        self.assertFalse(previous["cargo_id"])

    def test_planner_moves_cargo_on_a_started_trip(self):
        other = self._slot("LATER", 0.0)
        cargo = self._cargo(name="Box", weight=40.0, vehicle_space_id=self.space.id)
        self.trip.start_trip = True
        self.trip.assign_load_planner_cargo(cargo.id, other.id)
        self.assertEqual(cargo.order_id, self.trip)
        self.assertEqual(cargo.space_allocation_id.vehicle_space_id, other)

    def test_demo_places_freight_and_keeps_loose_cargo(self):
        slot = self._slot("ROW-03-LEFT", 0.0)
        placed = self._cargo(name="Freight", weight=40.0)
        loose = self._cargo(name="Loose cartons", weight=10.0)
        booked = self.env["tms.order"]._place_cargo_in_floor_space(
            placed, "ROW-03-LEFT"
        )
        self.assertTrue(booked)
        self.assertEqual(placed.space_allocation_id.vehicle_space_id, slot)
        self.assertFalse(loose.space_allocation_id)
        self.assertEqual(loose.order_id, placed.order_id)

    def test_planner_clears_the_space_and_keeps_the_trip(self):
        slot = self._slot("HOLD", 0.0)
        cargo = self._cargo(name="Box", weight=40.0, vehicle_space_id=slot.id)
        self.trip.start_trip = True
        listed = self.trip.get_load_planner_data()
        placed = next(row for row in listed["assigned"] if row["name"] == "Box")
        self.assertEqual(placed["id"], cargo.id)
        data = self.trip.release_load_planner_cargo(cargo.id)
        self.assertEqual(cargo.order_id, self.trip)
        self.assertFalse(cargo.space_allocation_id)
        self.assertIn(cargo.id, [row["id"] for row in data["loose"]])
        freed = next(row for row in data["allocations"] if row["code"] == "HOLD")
        self.assertEqual(freed["state"], "available")
        self.assertFalse(freed["cargo_id"])

    def _slot(self, code, pos_z, vehicle=None):
        vehicle = vehicle or self.vehicle
        layout = self.env["tms.vehicle.model.space"].create(
            {
                "model_id": vehicle.model_id.id,
                "code": code,
                "zone": "center",
                "pos_x": 1.0,
                "pos_y": 0.0,
                "pos_z": pos_z,
                "size_length": 1.2,
                "size_width": 1.2,
                "size_height": 1.2,
            }
        )
        return vehicle.space_ids.filtered(lambda space: space.model_space_id == layout)

    def test_upper_space_needs_stackable_cargo_below(self):
        floor = self._slot("FLOOR", 0.0)
        above = self._slot("ABOVE", 1.2)
        self._cargo(name="Floor", weight=40.0, vehicle_space_id=floor.id)
        upper = self._cargo(
            name="Upper", weight=40.0, vehicle_space_id=above.id
        )
        self.assertEqual(upper.space_allocation_id.vehicle_space_id, above)
        data = self.trip.get_load_planner_data()
        status = {row["code"]: row["status"] for row in data["spaces"]}
        self.assertEqual(status["FLOOR"], "stackable")
        self.assertEqual(status["ABOVE"], "stackable")
        with self.assertRaises(ValidationError):
            upper.order_id.cargo_ids.filtered(
                lambda line: line.space_allocation_id.vehicle_space_id == floor
            ).is_stackable = False

    def test_empty_or_top_load_blocks_the_space_above(self):
        floor = self._slot("BASE", 0.0)
        above = self._slot("HIGH", 1.2)
        data = self.trip.get_load_planner_data()
        status = {row["code"]: row["status"] for row in data["spaces"]}
        self.assertEqual(status["HIGH"], "blocked")
        self._cargo(
            name="Base",
            weight=40.0,
            vehicle_space_id=floor.id,
            is_stackable=False,
        )
        with self.assertRaises(ValidationError):
            self._cargo(name="High", weight=40.0, vehicle_space_id=above.id)

    def _trip_at(self, start, hours, vehicle=None):
        trip = self.env["tms.order"].create(
            {
                "origin_id": self.origin.id,
                "destination_id": self.destination.id,
                "vehicle_id": (vehicle or self.vehicle).id,
                "transport_type": "cargo",
            }
        )
        trip.write(
            {
                "scheduled_date_start": fields.Datetime.to_datetime(start),
                "scheduled_duration": hours,
            }
        )
        return trip

    def test_a_later_trip_reuses_the_space(self):
        self.trip.write(
            {
                "scheduled_date_start": fields.Datetime.to_datetime(
                    "2026-10-01 08:00:00"
                ),
                "scheduled_duration": 4.0,
            }
        )
        self._cargo(name="Morning", vehicle_space_id=self.space.id)
        later = self._trip_at("2026-10-01 12:00:00", 4.0)
        cargo = self._cargo(
            name="Afternoon",
            order_id=later.id,
            vehicle_space_id=self.space.id,
        )
        self.assertEqual(cargo.space_allocation_id.vehicle_space_id, self.space)
        status = later.get_load_planner_data()["spaces"][0]["status"]
        self.assertEqual(status, "stackable")

    def test_an_overlapping_trip_on_the_same_vehicle_is_refused(self):
        self.trip.write(
            {
                "scheduled_date_start": fields.Datetime.to_datetime(
                    "2026-10-01 08:00:00"
                ),
                "scheduled_duration": 8.0,
            }
        )
        self._cargo(name="Held", vehicle_space_id=self.space.id)
        with self.assertRaises(ValidationError):
            self._trip_at("2026-10-01 10:00:00", 4.0)

    def test_a_done_trip_releases_the_space(self):
        self.trip.write(
            {
                "scheduled_date_start": fields.Datetime.to_datetime(
                    "2026-10-01 08:00:00"
                ),
                "scheduled_duration": 8.0,
            }
        )
        self._cargo(name="Held", vehicle_space_id=self.space.id)
        self.trip.end_trip = True
        arrived = self._trip_at("2026-10-01 10:00:00", 4.0)
        status = arrived.get_load_planner_data()["spaces"][0]["status"]
        self.assertEqual(status, "empty")
        arrived.end_trip = True
        completed = self.env.ref("tms.tms_stage_order_completed")
        self.trip.write({"end_trip": False, "stage_id": completed.id})
        overlap = self._trip_at("2026-10-01 10:00:00", 4.0)
        self.assertEqual(
            overlap.get_load_planner_data()["spaces"][0]["status"], "empty"
        )
        cargo = self._cargo(
            name="Next",
            order_id=overlap.id,
            vehicle_space_id=self.space.id,
        )
        self.assertEqual(cargo.space_allocation_id.vehicle_space_id, self.space)

    def test_another_vehicle_can_use_the_same_space(self):
        self.trip.write(
            {
                "scheduled_date_start": fields.Datetime.to_datetime(
                    "2026-10-01 08:00:00"
                ),
                "scheduled_duration": 8.0,
            }
        )
        self._cargo(name="Held", vehicle_space_id=self.space.id)
        other_vehicle = self.env["fleet.vehicle"].create(
            {
                "model_id": self.model.id,
                "operation": "cargo",
                "license_plate": "PLAN-3",
            }
        )
        other = self._trip_at("2026-10-01 10:00:00", 4.0, vehicle=other_vehicle)
        other_space = other_vehicle.space_ids.filtered(
            lambda space: space.model_space_id == self.layout
        )
        cargo = self._cargo(
            name="Other truck",
            order_id=other.id,
            vehicle_space_id=other_space.id,
        )
        self.assertEqual(cargo.space_allocation_id.vehicle_space_id, other_space)
        self.assertNotEqual(other_space, self.space)

    def test_assigning_a_vehicle_fills_the_space_inventory(self):
        rows = self.trip.space_allocation_ids
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows.state, "available")
        self.assertEqual(rows.vehicle_space_id, self.space)
        cargo = self._cargo(name="Booked", vehicle_space_id=self.space.id)
        self.assertEqual(rows.cargo_id, cargo)
        self.assertEqual(rows.state, "booked")
        cargo.space_allocation_id = False
        self.assertFalse(rows.cargo_id)
        self.assertEqual(rows.state, "available")

    def test_vehicle_swap_refuses_a_booked_space_the_new_model_lacks(self):
        self._cargo(name="Booked", weight=40.0, vehicle_space_id=self.space.id)
        other_model = self.env["fleet.vehicle.model"].create(
            {
                "name": "Other Box",
                "brand_id": self.model.brand_id.id,
                "vehicle_type": "truck",
                "max_weight_capacity": 1000.0,
                "max_weight_uom_id": self.kilogram.id,
            }
        )
        self.env["tms.vehicle.model.space"].create(
            {
                "model_id": other_model.id,
                "code": "OTHER",
                "zone": "rear",
            }
        )
        other = self.env["fleet.vehicle"].create(
            {
                "model_id": other_model.id,
                "operation": "cargo",
                "license_plate": "PLAN-4",
            }
        )
        with self.assertRaises(ValidationError):
            self.trip.vehicle_id = other

    def test_vehicle_swap_keeps_a_booked_space_with_the_same_code(self):
        self._cargo(name="Booked", weight=40.0, vehicle_space_id=self.space.id)
        other_model = self.env["fleet.vehicle.model"].create(
            {
                "name": "Same Codes",
                "brand_id": self.model.brand_id.id,
                "vehicle_type": "truck",
                "max_weight_capacity": 1000.0,
                "max_weight_uom_id": self.kilogram.id,
            }
        )
        self.env["tms.vehicle.model.space"].create(
            {
                "model_id": other_model.id,
                "code": "ROW-1-LEFT",
                "zone": "front",
            }
        )
        other = self.env["fleet.vehicle"].create(
            {
                "model_id": other_model.id,
                "operation": "cargo",
                "license_plate": "PLAN-5",
            }
        )
        self.trip.vehicle_id = other
        booked = self.trip.space_allocation_ids.filtered(
            lambda row: row.state == "booked"
        )
        moved = other.space_ids.filtered(lambda space: space.code == "ROW-1-LEFT")
        self.assertEqual(booked.vehicle_space_id, moved)
        self.assertEqual(
            booked.cargo_id.space_allocation_id.vehicle_space_id, moved
        )

    def test_sale_line_reuses_the_service_fields(self):
        template = self.env["product.template"].create(
            {"name": "Planner haul", "type": "service"}
        )
        template.write(
            {
                "transport_type": "cargo",
                "transit_mode": "road",
                "booking_type": "shared_space",
            }
        )
        partner = self.env["res.partner"].create({"name": "Planner Customer"})
        order = self.env["sale.order"].create({"partner_id": partner.id})
        line = self.env["sale.order.line"].create(
            {
                "order_id": order.id,
                "product_id": template.product_variant_ids.id,
                "tms_origin_id": self.origin.id,
                "tms_destination_id": self.destination.id,
                "tms_trip_ticket_id": self.trip.id,
            }
        )
        self.assertEqual(line.transport_type, "cargo")
        self.assertEqual(line.transit_mode, "road")
        self.assertEqual(line.booking_type, "shared_space")
        self.assertEqual(line.origin_id, self.origin)
        self.assertEqual(line.destination_id, self.destination)
        self.assertEqual(line.trip_id, self.trip)

    def test_layout_plan_is_published_on_the_planner(self):
        data = self.trip.get_load_planner_data()
        self.assertFalse(data["layout_image_url"])
        png = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8"
            "z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
        )
        self.model.layout_image = png
        data = self.trip.get_load_planner_data()
        self.assertIn(
            "/web/image/fleet.vehicle.model/%s/layout_image" % self.model.id,
            data["layout_image_url"],
        )

    def test_vehicle_space_must_match_the_model(self):
        other_model = self.env["fleet.vehicle.model"].create(
            {
                "name": "Mismatch Box",
                "brand_id": self.model.brand_id.id,
                "vehicle_type": "truck",
            }
        )
        other_layout = self.env["tms.vehicle.model.space"].create(
            {
                "model_id": other_model.id,
                "code": "OTHER",
                "zone": "rear",
            }
        )
        with self.assertRaises(ValidationError):
            self.env["tms.vehicle.space"].create(
                {
                    "vehicle_id": self.vehicle.id,
                    "model_space_id": other_layout.id,
                }
            )

    def test_allocation_must_match_the_trip_vehicle(self):
        other_vehicle = self.env["fleet.vehicle"].create(
            {
                "model_id": self.model.id,
                "operation": "cargo",
                "license_plate": "PLAN-6",
            }
        )
        other_space = other_vehicle.space_ids[:1]
        with self.assertRaises(ValidationError):
            self.env["tms.trip.space.allocation"].create(
                {
                    "trip_id": self.trip.id,
                    "vehicle_space_id": other_space.id,
                }
            )

    def test_blocking_a_space_blocks_every_open_trip(self):
        self.trip.write(
            {
                "scheduled_date_start": fields.Datetime.to_datetime(
                    "2026-10-01 08:00:00"
                ),
                "scheduled_duration": 4.0,
            }
        )
        booked = self._cargo(name="Morning", vehicle_space_id=self.space.id)
        self.trip.end_trip = True
        later = self._trip_at("2026-10-01 08:00:00", 4.0)
        afternoon = self._trip_at("2026-10-01 14:00:00", 4.0)
        self.space.state = "blocked"
        done_row = self.trip.space_allocation_ids.filtered(
            lambda row: row.vehicle_space_id == self.space
        )
        self.assertEqual(done_row.state, "booked")
        self.assertEqual(booked.space_allocation_id.vehicle_space_id, self.space)
        for trip in later, afternoon:
            row = trip.space_allocation_ids.filtered(
                lambda line: line.vehicle_space_id == self.space
            )
            self.assertEqual(row.state, "blocked")
        with self.assertRaises(ValidationError):
            self._cargo(
                name="Refused",
                order_id=afternoon.id,
                vehicle_space_id=self.space.id,
            )

    def test_space_cargo_button_lists_trips_by_date(self):
        self.trip.write(
            {
                "scheduled_date_start": fields.Datetime.to_datetime(
                    "2026-10-02 08:00:00"
                ),
                "scheduled_duration": 4.0,
            }
        )
        newer = self._cargo(name="Newer", vehicle_space_id=self.space.id)
        self.trip.end_trip = True
        earlier = self._trip_at("2026-10-01 08:00:00", 4.0)
        older = self._cargo(
            name="Older",
            order_id=earlier.id,
            vehicle_space_id=self.space.id,
        )
        action = self.space.action_view_cargo()
        cargos = self.env["tms.cargo"].search(
            action["domain"], order="space_trip_date desc, id desc"
        )
        self.assertEqual(list(cargos), [newer, older])
        self.assertEqual(cargos.order_id, newer.order_id | older.order_id)
        self.assertEqual(self.space.cargo_count, 2)

    def test_a_blocked_vehicle_space_cannot_be_booked(self):
        self.space.state = "blocked"
        row = self.trip.space_allocation_ids
        self.assertEqual(row.state, "blocked")
        with self.assertRaises(ValidationError):
            self._cargo(name="Blocked", vehicle_space_id=self.space.id)
        data = self.trip.get_load_planner_data()
        self.assertEqual(data["allocations"][0]["state"], "blocked")

    def test_demo_models_and_vehicles_receive_spaces(self):
        model = self.env.ref("tms.model_volvo_fm")
        vehicle = self.env["fleet.vehicle"].create(
            {
                "model_id": model.id,
                "operation": "cargo",
                "license_plate": "FM-SPACE",
            }
        )
        self.env["fleet.vehicle.model"]._demo_ensure_spaces()
        self.assertFalse(
            self.env["fleet.vehicle.model"]._demo_models_without_spaces()
        )
        self.assertIn("ROW-01-LEFT", model.space_ids.mapped("code"))
        self.assertEqual(
            set(vehicle.space_ids.model_space_id.ids),
            set(model.space_ids.ids),
        )
        dolly = self.env.ref("tms.demo_model_dolly", raise_if_not_found=False)
        if dolly:
            self.assertFalse(dolly.space_ids)
            self.assertFalse(dolly._demo_space_slots())
