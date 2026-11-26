from odoo.tests.common import TransactionCase


class TestFleetVehicle(TransactionCase):
    @classmethod
    def setUpClass(self):
        super().setUpClass()

        self.uom_volume = self.env.ref("uom.product_uom_cubic_meter")

        self.team = self.env["tms.team"].create(
            {
                "name": "Test Team",
            }
        )

        self.vehicle = self.env["fleet.vehicle"].create(
            {
                "name": "Test Vehicle",
                "license_plate": "Test Plate",
                "model_id": self.env["fleet.vehicle.model"]
                .create(
                    {
                        "name": "Test Model",
                        "brand_id": self.env["fleet.vehicle.model.brand"]
                        .create({"name": "Test Brand"})
                        .id,
                    }
                )
                .id,
            }
        )

    def test_vehicle_creation(self):
        self.assertTrue(self.vehicle, "Vehicle wasn't created successfully")
        self.assertEqual(
            self.vehicle.name,
            "Test Brand/Test Model/Test Plate",
            "Vehicle name should be 'Test Vehicle'",
        )

    def test_truck_and_bus_types(self):
        selection = dict(
            self.env["fleet.vehicle.model"]
            ._fields["vehicle_type"]
            ._description_selection(self.env)
        )
        self.assertEqual(selection["truck"], "Truck")
        self.assertEqual(selection["bus"], "Bus")
        self.assertEqual(selection["boat"], "Boat")
        self.assertEqual(selection["plane"], "Plane")
        self.assertEqual(selection["van"], "Van")

        brand = self.env["fleet.vehicle.model.brand"].create({"name": "Demo Maker"})
        truck_model = self.env["fleet.vehicle.model"].create(
            {
                "name": "Demo Tractor",
                "brand_id": brand.id,
                "vehicle_type": "truck",
            }
        )
        truck = self.env["fleet.vehicle"].create(
            {
                "model_id": truck_model.id,
                "license_plate": "TRK-TEST",
            }
        )
        self.assertEqual(truck.vehicle_type, "truck")

        bus_model = self.env["fleet.vehicle.model"].create(
            {
                "name": "Demo Coach",
                "brand_id": brand.id,
                "vehicle_type": "bus",
            }
        )
        bus = self.env["fleet.vehicle"].create(
            {
                "model_id": bus_model.id,
                "license_plate": "BUS-TEST",
            }
        )
        self.assertEqual(bus.vehicle_type, "bus")

        boat_model = self.env["fleet.vehicle.model"].create(
            {
                "name": "Demo Vessel",
                "brand_id": brand.id,
                "vehicle_type": "boat",
                "max_weight_capacity": 12000,
                "max_volume_capacity": 40,
            }
        )
        self.assertEqual(boat_model.vehicle_type, "boat")
        self.assertEqual(boat_model.max_weight_capacity, 12000)
        self.assertEqual(boat_model.max_volume_capacity, 40)
        self.assertEqual(
            boat_model.max_weight_uom_id, self.env.ref("uom.product_uom_kgm")
        )
        self.assertEqual(
            boat_model.max_volume_uom_id,
            self.env.ref("uom.product_uom_cubic_meter"),
        )

    def test_car_and_van_cabin_fields(self):
        brand = self.env["fleet.vehicle.model.brand"].create({"name": "Van Maker"})
        van = self.env["fleet.vehicle.model"].create(
            {
                "name": "Demo Van",
                "brand_id": brand.id,
                "vehicle_type": "van",
                "trunk_volume": 3.5,
                "passenger_capacity": 8,
            }
        )
        self.assertEqual(van.trunk_volume, 3.5)
        self.assertEqual(van.passenger_capacity, 8)
        self.assertEqual(
            van.trunk_volume_uom_id, self.env.ref("uom.product_uom_cubic_meter")
        )
        arch = self.env.ref("tms.fleet_vehicle_model_view_form_tms").arch
        self.assertIn("vehicle_type not in ('car', 'van')", arch)

    def test_bus_compartment_fields(self):
        brand = self.env["fleet.vehicle.model.brand"].create({"name": "Bus Maker"})
        bus = self.env["fleet.vehicle.model"].create(
            {
                "name": "Demo Bus",
                "brand_id": brand.id,
                "vehicle_type": "bus",
                "belly_volume": 12.0,
                "belly_weight": 2500.0,
                "seats": 48,
                "standing_capacity": 12,
            }
        )
        self.assertEqual(bus.belly_volume, 12.0)
        self.assertEqual(bus.belly_weight, 2500.0)
        self.assertEqual(bus.seats, 48)
        self.assertEqual(bus.standing_capacity, 12)
        self.assertEqual(
            bus.belly_volume_uom_id, self.env.ref("uom.product_uom_cubic_meter")
        )
        self.assertEqual(
            bus.belly_weight_uom_id, self.env.ref("uom.product_uom_kgm")
        )
        arch = self.env.ref("tms.fleet_vehicle_model_view_form_tms").arch
        self.assertIn("vehicle_type != 'bus'", arch)

    def test_truck_loading_fields(self):
        brand = self.env["fleet.vehicle.model.brand"].create({"name": "Truck Maker"})
        truck = self.env["fleet.vehicle.model"].create(
            {
                "name": "Demo Truck",
                "brand_id": brand.id,
                "vehicle_type": "truck",
                "loading_length": 53.0,
                "pallet_capacity": 26,
                "max_axle_weight": 9000.0,
                "door_width": 2.4,
                "door_height": 2.7,
            }
        )
        self.assertEqual(truck.loading_length, 53.0)
        self.assertEqual(truck.pallet_capacity, 26)
        self.assertEqual(truck.max_axle_weight, 9000.0)
        self.assertEqual(truck.door_width, 2.4)
        self.assertEqual(truck.door_height, 2.7)
        self.assertEqual(
            truck.loading_length_uom_id, self.env.ref("uom.product_uom_km")
        )
        self.assertEqual(
            truck.door_dimension_uom_id, self.env.ref("uom.product_uom_km")
        )
        self.assertEqual(
            truck.max_axle_weight_uom_id, self.env.ref("uom.product_uom_kgm")
        )
        arch = self.env.ref("tms.fleet_vehicle_model_view_form_tms").arch
        self.assertIn("vehicle_type != 'truck'", arch)

    def test_boat_capacity_fields(self):
        brand = self.env["fleet.vehicle.model.brand"].create({"name": "Shipyard"})
        boat = self.env["fleet.vehicle.model"].create(
            {
                "name": "Demo Vessel Capacity",
                "brand_id": brand.id,
                "vehicle_type": "boat",
                "teu_capacity": 1800,
                "deadweight_tonnage": 25000.0,
                "draft_limit": 12.5,
            }
        )
        self.assertEqual(boat.teu_capacity, 1800)
        self.assertEqual(boat.deadweight_tonnage, 25000.0)
        self.assertEqual(boat.draft_limit, 12.5)
        self.assertEqual(boat.deadweight_uom_id, self.env.ref("uom.product_uom_kgm"))
        self.assertEqual(boat.draft_uom_id, self.env.ref("uom.product_uom_km"))
        self.assertIn("bulk cargo ships", boat._fields["deadweight_tonnage"].help)
        self.assertIn("certain ports", boat._fields["draft_limit"].help)
        arch = self.env.ref("tms.fleet_vehicle_model_view_form_tms").arch
        self.assertIn("vehicle_type != 'boat'", arch)

    def test_plane_capacity_fields(self):
        brand = self.env["fleet.vehicle.model.brand"].create({"name": "Airframe"})
        plane = self.env["fleet.vehicle.model"].create(
            {
                "name": "Demo Freighter",
                "brand_id": brand.id,
                "vehicle_type": "plane",
                "position_slots": 30,
                "max_takeoff_weight": 396000.0,
                "floor_loading_limit": 1500.0,
            }
        )
        self.assertEqual(plane.position_slots, 30)
        self.assertEqual(plane.max_takeoff_weight, 396000.0)
        self.assertEqual(plane.floor_loading_limit, 1500.0)
        self.assertEqual(
            plane.max_takeoff_weight_uom_id, self.env.ref("uom.product_uom_kgm")
        )
        self.assertEqual(plane.floor_loading_uom_id, self.env.ref("tms.uom_kg_per_m2"))
        self.assertIn("air containers", plane._fields["position_slots"].help)
        self.assertIn("airport altitude", plane._fields["max_takeoff_weight"].help)
        self.assertIn("cabin floor", plane._fields["floor_loading_limit"].help)
        arch = self.env.ref("tms.fleet_vehicle_model_view_form_tms").arch
        self.assertIn("vehicle_type != 'plane'", arch)

    def test_default_volume_uom(self):
        model = self.env["fleet.vehicle.model"].create(
            {
                "name": "Volume Model",
                "brand_id": self.vehicle.model_id.brand_id.id,
            }
        )
        self.assertEqual(model.max_volume_uom_id, self.uom_volume)

    def test_odometer_menu_groups_by_vehicle(self):
        action = self.env.ref("tms.action_tms_odometer")
        menu = self.env.ref("tms.menu_fleet_odometers")
        view = self.env.ref("tms.fleet_vehicle_odometer_view_tree_tms")
        self.assertEqual(menu.action, action)
        self.assertIn("search_default_groupby_vehicle", action.context)
        self.assertIn("date desc, id desc", view.arch)

    def test_odometer_date_is_a_timestamp(self):
        field = self.env["fleet.vehicle.odometer"]._fields["date"]
        self.assertEqual(field.type, "datetime")
        self.assertEqual(field.string, "Timestamp")
