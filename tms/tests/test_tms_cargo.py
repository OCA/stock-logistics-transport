# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestTMSCargo(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        brand = cls.env["fleet.vehicle.model.brand"].create({"name": "Cargo Brand"})
        cls.cubic_meter = cls.env.ref("uom.product_uom_cubic_meter")
        cls.kilogram = cls.env.ref("uom.product_uom_kgm")
        model = cls.env["fleet.vehicle.model"].create(
            {
                "name": "Cargo Model",
                "brand_id": brand.id,
                "max_volume_capacity": 10.0,
                "max_volume_uom_id": cls.cubic_meter.id,
            }
        )
        cls.cargo_vehicle = cls.env["fleet.vehicle"].create(
            {
                "name": "Cargo Truck",
                "model_id": model.id,
                "operation": "cargo",
            }
        )
        cls.passenger_vehicle = cls.env["fleet.vehicle"].create(
            {
                "name": "Passenger Bus",
                "model_id": model.id,
                "operation": "passenger",
            }
        )
        cls.origin = cls.env["res.partner"].create(
            {"name": "Cargo Origin", "tms_location": True}
        )
        cls.destination = cls.env["res.partner"].create(
            {"name": "Cargo Destination", "tms_location": True}
        )

    def _create_trip(self, **extra):
        values = {
            "origin_id": self.origin.id,
            "destination_id": self.destination.id,
        }
        values.update(extra)
        return self.env["tms.order"].create(values)

    def _cargo_vals(self, **extra):
        values = {
            "name": "Crates",
            "quantity": 2.0,
            "weight": 500.0,
            "weight_uom_id": self.kilogram.id,
            "volume": 4.0,
            "volume_uom_id": self.cubic_meter.id,
            "packaging": "Crates",
        }
        values.update(extra)
        return values

    def test_missing_state_defaults_to_planned(self):
        cargo = self.env["tms.cargo"].create(
            self._cargo_vals(name="Refri", state=False)
        )
        self.assertEqual(cargo.state, "planned")

    def test_cargo_page_is_limited_to_cargo_vehicles(self):
        arch = self.env["tms.order"].get_view(view_type="form")["arch"]
        self.assertIn('name="cargo_page"', arch)
        self.assertIn("transport_type != 'cargo'", arch)

    def test_transport_type_filters_vehicles(self):
        trip = self._create_trip(
            vehicle_id=self.cargo_vehicle.id,
        )
        self.assertEqual(trip.transport_type, "cargo")
        self.assertIn(self.cargo_vehicle, trip.vehicle_ids_domain)
        self.assertNotIn(self.passenger_vehicle, trip.vehicle_ids_domain)
        trip.transport_type = "passenger"
        self.assertFalse(trip.vehicle_id)
        self.assertIn(self.passenger_vehicle, trip.vehicle_ids_domain)
        self.assertNotIn(self.cargo_vehicle, trip.vehicle_ids_domain)

    def test_vehicle_must_match_transport_type(self):
        trip = self._create_trip(transport_type="passenger")
        with self.assertRaises(ValidationError):
            trip.vehicle_id = self.cargo_vehicle

    def test_cargo_vehicle_accepts_cargo_and_totals(self):
        trip = self._create_trip(vehicle_id=self.cargo_vehicle.id)
        self.env["tms.cargo"].create(self._cargo_vals(order_id=trip.id, weight=1500.0))
        self.assertEqual(trip.vehicle_operation, "cargo")
        self.assertEqual(trip.cargo_weight, 1500.0)
        self.assertEqual(trip.cargo_volume, 4.0)

    def test_passenger_vehicle_rejects_cargo(self):
        trip = self._create_trip(vehicle_id=self.passenger_vehicle.id)
        with self.assertRaises(ValidationError):
            self.env["tms.cargo"].create(self._cargo_vals(order_id=trip.id))

    def test_switching_to_passenger_vehicle_rejects_existing_cargo(self):
        trip = self._create_trip(vehicle_id=self.cargo_vehicle.id)
        self.env["tms.cargo"].create(self._cargo_vals(order_id=trip.id))
        with self.assertRaises(ValidationError):
            trip.vehicle_id = self.passenger_vehicle

    def test_cargo_trip_requires_cargo_to_start(self):
        trip = self._create_trip(vehicle_id=self.cargo_vehicle.id)
        with self.assertRaises(UserError):
            trip.button_start_order()

    def test_cargo_over_capacity_cannot_start(self):
        trip = self._create_trip(vehicle_id=self.cargo_vehicle.id)
        self.env["tms.cargo"].create(self._cargo_vals(order_id=trip.id, volume=20.0))
        with self.assertRaises(UserError):
            trip.button_start_order()

    def test_cargo_must_be_loaded_before_start(self):
        trip = self._create_trip(vehicle_id=self.cargo_vehicle.id)
        self.env["tms.cargo"].create(self._cargo_vals(order_id=trip.id, volume=4.0))
        trip.stage_id = self.env.ref("tms.tms_stage_order_confirmed")
        with self.assertRaises(UserError):
            trip.button_start_order()

    def test_cargo_within_capacity_can_start(self):
        trip = self._create_trip(vehicle_id=self.cargo_vehicle.id)
        cargo = self.env["tms.cargo"].create(
            self._cargo_vals(order_id=trip.id, volume=4.0)
        )
        trip.stage_id = self.env.ref("tms.tms_stage_order_confirmed")
        cargo.state = "loaded"
        self.assertEqual(trip.stage_id, self.env.ref("tms.tms_stage_order_loaded"))
        trip.button_start_order()
        self.assertTrue(trip.start_trip)
        self.assertEqual(trip.stage_id, self.env.ref("tms.tms_stage_order_in_transit"))

    def test_split_trip_copies_the_route_without_cargo(self):
        trip = self._create_trip(vehicle_id=self.cargo_vehicle.id)
        self.env["tms.cargo"].create(self._cargo_vals(order_id=trip.id))
        action = trip.action_split_trip()
        new_trip = self.env["tms.order"].browse(action["res_id"])
        self.assertEqual(new_trip.origin_id, trip.origin_id)
        self.assertEqual(new_trip.destination_id, trip.destination_id)
        self.assertEqual(new_trip.stage_id, trip.stage_id)
        self.assertFalse(new_trip.cargo_ids)
        self.assertTrue(trip.cargo_ids)

    def test_cargo_cannot_move_after_the_trip_starts(self):
        trip = self._create_trip(vehicle_id=self.cargo_vehicle.id)
        cargo = self.env["tms.cargo"].create(
            self._cargo_vals(order_id=trip.id, volume=4.0)
        )
        other = self._create_trip(vehicle_id=self.cargo_vehicle.id)
        trip.stage_id = self.env.ref("tms.tms_stage_order_confirmed")
        cargo.state = "loaded"
        trip.button_start_order()
        with self.assertRaises(UserError):
            cargo.order_id = other
        with self.assertRaises(UserError):
            trip.action_split_trip()

    def test_passenger_trip_starts_without_cargo(self):
        trip = self._create_trip(vehicle_id=self.passenger_vehicle.id)
        trip.button_start_order()
        self.assertTrue(trip.start_trip)

    def _box(self, plate, volume=0.0, weight=0.0, equipment_type="trailer"):
        model = self.env["fleet.vehicle.model"].create(
            {
                "name": plate,
                "brand_id": self.cargo_vehicle.model_id.brand_id.id,
                "max_volume_capacity": volume,
                "max_volume_uom_id": self.cubic_meter.id,
                "max_weight_capacity": weight,
                "max_weight_uom_id": self.kilogram.id,
            }
        )
        return self.env["fleet.vehicle"].create(
            {
                "model_id": model.id,
                "license_plate": plate,
                "tms_equipment_type": equipment_type,
            }
        )

    def test_unset_payload_does_not_block_start(self):
        trip = self._create_trip(vehicle_id=self.cargo_vehicle.id)
        cargo = self.env["tms.cargo"].create(
            self._cargo_vals(order_id=trip.id, volume=4.0, weight=500.0)
        )
        self.assertFalse(trip.weight_capacity_set)
        self.assertEqual(trip.remaining_weight, -500.0)
        self.assertTrue(trip.volume_capacity_set)
        self.assertEqual(trip.capacity_volume, 10.0)
        self.assertEqual(trip.remaining_volume, 6.0)
        trip.stage_id = self.env.ref("tms.tms_stage_order_confirmed")
        cargo.state = "loaded"
        trip.button_start_order()
        self.assertTrue(trip.start_trip)

    def test_overweight_cargo_cannot_start(self):
        self.cargo_vehicle.model_id.max_weight_capacity = 100.0
        self.cargo_vehicle.model_id.max_weight_uom_id = self.kilogram
        trip = self._create_trip(vehicle_id=self.cargo_vehicle.id)
        self.env["tms.cargo"].create(
            self._cargo_vals(order_id=trip.id, volume=4.0, weight=500.0)
        )
        self.assertEqual(trip.capacity_weight, 100.0)
        self.assertEqual(trip.remaining_weight, -400.0)
        with self.assertRaises(UserError):
            trip.button_start_order()

    def test_coupled_trailer_replaces_the_tractor_volume(self):
        trip = self._create_trip(vehicle_id=self.cargo_vehicle.id)
        trailer = self._box("BOX-1", volume=30.0, weight=8000.0)
        self.env["tms.order.equipment"].create(
            {"order_id": trip.id, "vehicle_id": trailer.id}
        )
        self.env["tms.cargo"].create(
            self._cargo_vals(order_id=trip.id, volume=12.0, weight=1000.0)
        )
        self.assertEqual(trip.capacity_volume, 30.0)
        self.assertEqual(trip.remaining_volume, 18.0)

    def test_two_trailers_add_their_volume(self):
        trip = self._create_trip(vehicle_id=self.cargo_vehicle.id)
        first = self._box("BOX-A", volume=30.0)
        second = self._box("BOX-B", volume=20.0)
        for trailer in (first, second):
            self.env["tms.order.equipment"].create(
                {"order_id": trip.id, "vehicle_id": trailer.id}
            )
        self.assertEqual(trip.capacity_volume, 50.0)

    def test_dropped_trailer_and_dolly_are_ignored(self):
        trip = self._create_trip(vehicle_id=self.cargo_vehicle.id)
        dropped = self._box("BOX-DROP", volume=30.0, weight=9000.0)
        dolly = self._box("DOLLY-1", volume=99.0, weight=99.0, equipment_type="dolly")
        self.env["tms.order.equipment"].create(
            {
                "order_id": trip.id,
                "vehicle_id": dropped.id,
                "dropped": True,
            }
        )
        self.env["tms.order.equipment"].create(
            {"order_id": trip.id, "vehicle_id": dolly.id}
        )
        self.assertEqual(trip.capacity_volume, 10.0)
        self.assertFalse(trip.weight_capacity_set)

    def test_weight_limit_is_the_lower_payload(self):
        self.cargo_vehicle.model_id.max_weight_capacity = 10000.0
        self.cargo_vehicle.model_id.max_weight_uom_id = self.kilogram
        trip = self._create_trip(vehicle_id=self.cargo_vehicle.id)
        trailer = self._box("BOX-W", volume=40.0, weight=8000.0)
        self.env["tms.order.equipment"].create(
            {"order_id": trip.id, "vehicle_id": trailer.id}
        )
        self.env["tms.cargo"].create(
            self._cargo_vals(order_id=trip.id, volume=4.0, weight=9000.0)
        )
        self.assertEqual(trip.capacity_weight, 8000.0)
        with self.assertRaises(UserError):
            trip.button_start_order()

    def test_passenger_seats_are_not_a_volume_limit(self):
        trip = self._create_trip(vehicle_id=self.passenger_vehicle.id)
        self.assertFalse(trip.volume_capacity_set)
        self.assertFalse(trip.weight_capacity_set)

    def test_totals_use_the_configured_uom(self):
        tonne = self.env.ref("uom.product_uom_ton")
        litre = self.env.ref("uom.product_uom_litre")
        params = self.env["ir.config_parameter"].sudo()
        params.set_param("tms.default_weight_uom", str(tonne.id))
        params.set_param("tms.default_volume_uom", str(litre.id))
        trip = self._create_trip(vehicle_id=self.cargo_vehicle.id)
        self.env["tms.cargo"].create(
            self._cargo_vals(order_id=trip.id, weight=1500.0, volume=4.0)
        )
        trip.invalidate_recordset()
        self.assertEqual(trip.cargo_weight_uom_id, tonne)
        self.assertEqual(trip.cargo_volume_uom_id, litre)
        self.assertAlmostEqual(trip.cargo_weight, 1.5)
        self.assertAlmostEqual(trip.cargo_volume, 4000.0)
        self.assertAlmostEqual(trip.capacity_volume, 10000.0)

    def test_new_model_uses_the_configured_units(self):
        tonne = self.env.ref("uom.product_uom_ton")
        litre = self.env.ref("uom.product_uom_litre")
        params = self.env["ir.config_parameter"].sudo()
        params.set_param("tms.default_weight_uom", str(tonne.id))
        params.set_param("tms.default_volume_uom", str(litre.id))
        model = self.env["fleet.vehicle.model"].create(
            {
                "name": "Configured Units",
                "brand_id": self.cargo_vehicle.model_id.brand_id.id,
            }
        )
        self.assertEqual(model.max_weight_uom_id, tonne)
        self.assertEqual(model.max_volume_uom_id, litre)

    def test_hold_drops_the_line_from_the_trip_total(self):
        trip = self._create_trip(vehicle_id=self.cargo_vehicle.id)
        kept = self.env["tms.cargo"].create(
            self._cargo_vals(order_id=trip.id, weight=200.0, volume=1.0)
        )
        held = self.env["tms.cargo"].create(
            self._cargo_vals(order_id=trip.id, name="Late", weight=800.0, volume=3.0)
        )
        held.action_put_on_hold()
        self.assertEqual(held.state, "hold")
        self.assertEqual(held.order_id, trip)
        self.assertEqual(trip.cargo_weight, 200.0)
        self.assertEqual(trip.cargo_volume, 1.0)
        trip.stage_id = self.env.ref("tms.tms_stage_order_confirmed")
        kept.state = "loaded"
        trip.button_start_order()
        self.assertTrue(trip.start_trip)

    def test_hold_only_trip_can_leave(self):
        trip = self._create_trip(vehicle_id=self.cargo_vehicle.id)
        cargo = self.env["tms.cargo"].create(self._cargo_vals(order_id=trip.id))
        cargo.action_put_on_hold()
        trip.stage_id = self.env.ref("tms.tms_stage_order_confirmed")
        trip.button_start_order()
        self.assertTrue(trip.start_trip)

    def test_return_to_pool_clears_the_trip(self):
        trip = self._create_trip(vehicle_id=self.cargo_vehicle.id)
        cargo = self.env["tms.cargo"].create(self._cargo_vals(order_id=trip.id))
        cargo.action_return_to_pool()
        self.assertFalse(cargo.order_id)
        self.assertEqual(cargo.state, "unassigned")
        self.assertFalse(trip.cargo_ids)

    def test_unassigned_menu_filters_by_default(self):
        action = self.env.ref("tms.action_tms_cargo_pool")
        self.assertEqual(action.domain, "[]")
        self.assertIn("search_default_unassigned", action.context)
        arch = self.env.ref("tms.tms_cargo_view_search").arch
        self.assertIn('name="unassigned"', arch)
        self.assertIn("('state', '=', 'unassigned')", arch)

    def test_cargo_form_has_a_chatter(self):
        cargo = self.env["tms.cargo"]
        self.assertIn("message_ids", cargo._fields)
        self.assertIn("activity_ids", cargo._fields)
        arch = self.env.ref("tms.tms_cargo_view_form").arch
        self.assertIn("<chatter", arch)
        self.assertIn("weight_uom_id", arch)

    def test_split_line_keeps_the_remainder(self):
        trip = self._create_trip(vehicle_id=self.cargo_vehicle.id)
        cargo = self.env["tms.cargo"].create(
            self._cargo_vals(order_id=trip.id, quantity=4.0, weight=400.0, volume=4.0)
        )
        wizard = self.env["tms.cargo.split"].create(
            {
                "cargo_id": cargo.id,
                "quantity": 1.0,
                "weight": 100.0,
                "volume": 1.0,
            }
        )
        wizard.action_apply()
        lines = trip.cargo_ids
        self.assertEqual(len(lines), 2)
        self.assertEqual(sum(lines.mapped("quantity")), 4.0)
        self.assertEqual(sum(lines.mapped("weight")), 400.0)
        self.assertEqual(cargo.quantity, 3.0)

    def test_reassign_moves_the_line(self):
        origin = self._create_trip(vehicle_id=self.cargo_vehicle.id)
        target = self._create_trip(vehicle_id=self.cargo_vehicle.id)
        cargo = self.env["tms.cargo"].create(self._cargo_vals(order_id=origin.id))
        wizard = self.env["tms.cargo.reassign"].create(
            {"cargo_id": cargo.id, "trip_id": target.id}
        )
        wizard.action_apply()
        self.assertEqual(cargo.order_id, target)
        self.assertFalse(origin.cargo_ids)

    def test_swap_exchanges_lighter_cargo_on_the_same_destination(self):
        heavy_trip = self._create_trip(vehicle_id=self.cargo_vehicle.id)
        light_trip = self._create_trip(vehicle_id=self.cargo_vehicle.id)
        heavy = self.env["tms.cargo"].create(
            self._cargo_vals(order_id=heavy_trip.id, name="Heavy", weight=900.0)
        )
        light = self.env["tms.cargo"].create(
            self._cargo_vals(order_id=light_trip.id, name="Light", weight=100.0)
        )
        self.assertIn(light, heavy._swap_candidates())
        wizard = self.env["tms.cargo.swap"].create(
            {"cargo_id": heavy.id, "candidate_id": light.id}
        )
        wizard.action_apply()
        self.assertEqual(heavy.order_id, light_trip)
        self.assertEqual(light.order_id, heavy_trip)

    def test_loading_allocated_sums_pieces(self):
        trip = self._create_trip(vehicle_id=self.cargo_vehicle.id)
        self.env["tms.cargo"].create(
            self._cargo_vals(order_id=trip.id, quantity=5.0)
        )
        self.env["tms.cargo"].create(
            self._cargo_vals(order_id=trip.id, quantity=10.0)
        )
        held = self.env["tms.cargo"].create(
            self._cargo_vals(order_id=trip.id, quantity=4.0)
        )
        held.action_put_on_hold()
        self.assertFalse(trip.loading_uses_length)
        self.assertFalse(trip.cargo_loading_uom_id)
        self.assertEqual(trip.cargo_pieces, 15.0)
        self.assertEqual(
            trip.remaining_loading_meters,
            trip.capacity_loading_meters - 15.0,
        )

    def test_unit_pieces_use_pallet_capacity(self):
        self.cargo_vehicle.model_id.pallet_capacity = 26
        trip = self._create_trip(vehicle_id=self.cargo_vehicle.id)
        unit = self.env.ref("uom.product_uom_unit")
        self.env["tms.cargo"].create(
            self._cargo_vals(order_id=trip.id, quantity=10.0, uom_id=unit.id)
        )
        self.assertFalse(trip.loading_uses_length)
        self.assertFalse(trip.cargo_loading_uom_id)
        self.assertEqual(trip.capacity_loading_meters, 26.0)
        self.assertEqual(trip.cargo_pieces, 10.0)
        self.assertEqual(trip.remaining_loading_meters, 16.0)

    def test_meter_pieces_use_loading_length(self):
        meter = self.env.ref("uom.product_uom_meter")
        self.cargo_vehicle.model_id.write(
            {
                "loading_length": 15.0,
                "loading_length_uom_id": meter.id,
                "pallet_capacity": 26,
            }
        )
        trip = self._create_trip(vehicle_id=self.cargo_vehicle.id)
        self.env["tms.cargo"].create(
            self._cargo_vals(order_id=trip.id, quantity=4.0, uom_id=meter.id)
        )
        self.env["tms.cargo"].create(
            self._cargo_vals(order_id=trip.id, quantity=6.0, uom_id=meter.id)
        )
        self.assertTrue(trip.loading_uses_length)
        self.assertEqual(trip.cargo_loading_uom_id, meter)
        self.assertEqual(trip.capacity_loading_meters, 15.0)
        self.assertEqual(trip.cargo_pieces, 10.0)
        self.assertEqual(trip.remaining_loading_meters, 5.0)

    def test_foot_pieces_convert_the_loading_length(self):
        meter = self.env.ref("uom.product_uom_meter")
        foot = self.env.ref("uom.product_uom_foot")
        self.cargo_vehicle.model_id.write(
            {
                "loading_length": 15.0,
                "loading_length_uom_id": meter.id,
            }
        )
        trip = self._create_trip(vehicle_id=self.cargo_vehicle.id)
        self.env["tms.cargo"].create(
            self._cargo_vals(order_id=trip.id, quantity=10.0, uom_id=foot.id)
        )
        expected = meter._compute_quantity(15.0, foot)
        self.assertTrue(trip.loading_uses_length)
        self.assertEqual(trip.cargo_loading_uom_id, foot)
        self.assertEqual(trip.capacity_loading_meters, expected)
        self.assertEqual(trip.cargo_pieces, 10.0)
        self.assertEqual(trip.remaining_loading_meters, expected - 10.0)

    def test_top_load_doubles_the_floor_used(self):
        trip = self._create_trip(vehicle_id=self.cargo_vehicle.id)
        cargo = self.env["tms.cargo"].create(
            self._cargo_vals(order_id=trip.id, loading_meters=1.2)
        )
        self.assertEqual(trip.cargo_loading_meters, 1.2)
        cargo.action_toggle_top_load()
        self.assertFalse(cargo.is_stackable)
        self.assertEqual(trip.cargo_loading_meters, 2.4)
        cargo.action_toggle_top_load()
        self.assertEqual(trip.cargo_loading_meters, 1.2)

    def test_condition_note_is_stored_on_the_line(self):
        cargo = self.env["tms.cargo"].create(self._cargo_vals())
        attachment = self.env["ir.attachment"].create(
            {
                "name": "wrap.jpg",
                "datas": "aGVsbG8=",
                "res_model": "tms.cargo.condition",
            }
        )
        wizard = self.env["tms.cargo.condition"].create(
            {
                "cargo_id": cargo.id,
                "note": "Wrap is torn",
                "attachment_ids": [(6, 0, attachment.ids)],
            }
        )
        wizard.action_apply()
        self.assertEqual(cargo.condition_note, "Wrap is torn")
        self.assertEqual(cargo.condition_attachment_ids, attachment)
