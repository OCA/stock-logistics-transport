# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestTMSCargo(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        brand = cls.env["fleet.vehicle.model.brand"].create({"name": "Cargo Brand"})
        model = cls.env["fleet.vehicle.model"].create(
            {"name": "Cargo Model", "brand_id": brand.id}
        )
        cls.cubic_meter = cls.env.ref("uom.product_uom_cubic_meter")
        cls.kilogram = cls.env.ref("uom.product_uom_kgm")
        cls.cargo_vehicle = cls.env["fleet.vehicle"].create(
            {
                "name": "Cargo Truck",
                "model_id": model.id,
                "operation": "cargo",
                "capacity": 10.0,
                "cargo_uom_id": cls.cubic_meter.id,
            }
        )
        cls.passenger_vehicle = cls.env["fleet.vehicle"].create(
            {
                "name": "Passenger Bus",
                "model_id": model.id,
                "operation": "passenger",
                "capacity": 40.0,
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

    def test_cargo_page_is_limited_to_cargo_vehicles(self):
        arch = self.env["tms.order"].get_view(view_type="form")["arch"]
        self.assertIn('name="cargo_page"', arch)
        self.assertIn("vehicle_operation != 'cargo'", arch)

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
        return self.env["fleet.vehicle"].create(
            {
                "model_id": self.cargo_vehicle.model_id.id,
                "license_plate": plate,
                "tms_equipment_type": equipment_type,
                "capacity": volume,
                "cargo_uom_id": self.cubic_meter.id,
                "weight_capacity": weight,
                "weight_uom_id": self.kilogram.id,
            }
        )

    def test_unset_payload_does_not_block_start(self):
        trip = self._create_trip(vehicle_id=self.cargo_vehicle.id)
        cargo = self.env["tms.cargo"].create(
            self._cargo_vals(order_id=trip.id, volume=4.0, weight=500.0)
        )
        self.assertFalse(trip.weight_capacity_set)
        self.assertEqual(trip.remaining_weight, 0.0)
        self.assertTrue(trip.volume_capacity_set)
        self.assertEqual(trip.capacity_volume, 10.0)
        self.assertEqual(trip.remaining_volume, 6.0)
        trip.stage_id = self.env.ref("tms.tms_stage_order_confirmed")
        cargo.state = "loaded"
        trip.button_start_order()
        self.assertTrue(trip.start_trip)

    def test_overweight_cargo_cannot_start(self):
        self.cargo_vehicle.weight_capacity = 100.0
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
        self.cargo_vehicle.weight_capacity = 10000.0
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

    def test_new_vehicle_uses_the_configured_units(self):
        tonne = self.env.ref("uom.product_uom_ton")
        litre = self.env.ref("uom.product_uom_litre")
        params = self.env["ir.config_parameter"].sudo()
        params.set_param("tms.default_weight_uom", str(tonne.id))
        params.set_param("tms.default_volume_uom", str(litre.id))
        vehicle = self.env["fleet.vehicle"].create(
            {
                "model_id": self.cargo_vehicle.model_id.id,
                "operation": "cargo",
                "license_plate": "UOM-1",
            }
        )
        self.assertEqual(vehicle.weight_uom_id, tonne)
        self.assertEqual(vehicle.cargo_uom_id, litre)
