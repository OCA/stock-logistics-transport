# Copyright 2022 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
import base64
import codecs
import csv
import io
from datetime import datetime

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo import fields
from odoo.modules.module import get_resource_path
from odoo.tests import Form, SavepointCase

from .. import const

_reader = codecs.getreader("utf-8")


class TestMaxoptra(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.context = dict(cls.env.context, tracking_disable=True)
        # Stock
        cls.warehouse = cls.env.ref("stock.warehouse0")
        cls.stock_location = cls.env.ref("stock.stock_location_stock")
        cls.delivery_orders_picking_type = cls.env.ref("stock.picking_type_out")
        # Partners
        # Fremont, CA
        cls.partner_azure = cls.env.ref("base.res_partner_12")
        # Pleasant Hill, CA
        cls.partner_deco_addict = cls.env.ref("base.res_partner_2")
        # Fairfield, CA
        cls.partner_gemini = cls.env.ref("base.res_partner_3")
        # Stockton, CA
        cls.partner_lumber = cls.env.ref("base.res_partner_18")
        # Tracy, CA
        cls.partner_jackson = cls.env.ref("base.res_partner_10")
        cls.partner_ready = cls.env.ref("base.res_partner_4")
        # Vehicles
        cls.vehicle1 = cls.env.ref("shipment_planning_maxoptra.demo_vehicle_1")
        cls.vehicle2 = cls.env.ref("shipment_planning_maxoptra.demo_vehicle_2")
        cls.vehicle3 = cls.env.ref("shipment_planning_maxoptra.demo_vehicle_3")
        # Drivers
        cls.driver1 = cls._create_partner_driver("Driver 1", "Driver of Demo vehicle 1")
        cls.driver2 = cls._create_partner_driver("Driver 2", "Driver of Demo vehicle 2")
        cls.driver3 = cls._create_partner_driver("Driver 3", "Driver of Demo vehicle 3")
        # Product
        cls.product = cls.env.ref("stock.product_cable_management_box")
        cls.env["stock.quant"]._update_available_quantity(
            cls.product, cls.stock_location, 1000
        )
        # Schedule
        cls.delivery_scheduled_date = cls._get_delivery_scheduled_date_from_csv()

    @classmethod
    def _get_csv_reader(cls, content, decode=False):
        if decode:
            content = base64.b64decode(content)
        return csv.DictReader(_reader(io.BytesIO(content)))

    @classmethod
    def _create_partner_driver(cls, partner_name, driver_name):
        return cls.env["res.partner"].create(
            {
                "name": partner_name,
                "maxoptra_driver_name": driver_name,
            }
        )

    @classmethod
    def _create_delivery_order(cls, partner):
        picking_form = Form(cls.env["stock.picking"])
        picking_form.partner_id = partner
        picking_form.picking_type_id = cls.delivery_orders_picking_type
        with picking_form.move_ids_without_package.new() as move_form:
            move_form.product_id = cls.product
            move_form.product_uom_qty = 10.0
        return picking_form.save()

    @classmethod
    def _create_all_delivery_orders(cls):
        cls.delivery_azure = cls._create_delivery_order(cls.partner_azure)
        cls.delivery_deco_addict = cls._create_delivery_order(cls.partner_deco_addict)
        cls.delivery_gemini = cls._create_delivery_order(cls.partner_gemini)
        cls.delivery_lumber = cls._create_delivery_order(cls.partner_lumber)
        cls.delivery_jackson = cls._create_delivery_order(cls.partner_jackson)
        cls.delivery_ready = cls._create_delivery_order(cls.partner_ready)
        return cls.env["stock.picking"].browse(
            [
                cls.delivery_azure.id,
                cls.delivery_deco_addict.id,
                cls.delivery_gemini.id,
                cls.delivery_lumber.id,
                cls.delivery_jackson.id,
                cls.delivery_ready.id,
            ]
        )

    @classmethod
    def _create_shipment_planning(cls, pickings):
        shipment_planning_form = Form(cls.env["shipment.planning"])
        shipment_planning_form.maxoptra_planning = True
        for pick in pickings:
            shipment_planning_form.picking_to_plan_ids.add(pick)
        shipment_planning = shipment_planning_form.save()
        return shipment_planning

    @classmethod
    def _get_previous_pickings(cls, pickings):
        return pickings.mapped("move_lines.move_orig_ids.picking_id")

    @classmethod
    def _get_delivery_scheduled_date_from_csv(cls):
        maxoptra_file_path = get_resource_path(
            "shipment_planning_maxoptra", "tests", "data", "Schedules_25_01_2022.csv"
        )
        delivery_scheduled_date = {}
        with open(maxoptra_file_path, "rb") as maxoptra_file:
            csv_reader = cls._get_csv_reader(maxoptra_file.read())
            for row in csv_reader:
                delivery_scheduled_date[row.get("Order reference")] = datetime.strptime(
                    row.get("Scheduled arrival time"), const.MAXOPTRA_DATETIME_FORMAT
                )
        return delivery_scheduled_date

    def setUp(self):
        super().setUp()
        self._reset_delivery_orders_sequence()

    def _reset_delivery_orders_sequence(self):
        # Update sequence to ensure created pickings match with CSV data
        delivery_orders_sequence = self.delivery_orders_picking_type.sequence_id
        delivery_orders_sequence.write(
            {
                "prefix": delivery_orders_sequence.prefix + "1",
                "number_next_actual": 1,
            }
        )

    def test_csv_generation(self):
        delivery_pickings = self._create_all_delivery_orders()
        delivery_pickings.action_confirm()
        delivery_pickings.action_assign()
        shipment_planning = self._create_shipment_planning(delivery_pickings)
        shipment_planning.action_confirm()
        self.assertFalse(shipment_planning.maxoptra_to_import_file)
        shipment_planning.action_in_progress()
        self.assertTrue(shipment_planning.maxoptra_to_import_file)
        csv_reader = self._get_csv_reader(
            shipment_planning.maxoptra_to_import_file, decode=True
        )
        for row in csv_reader:
            picking_number = row.get("orderReference")
            picking = self.env["stock.picking"].search([("name", "=", picking_number)])
            self.assertIn(picking, delivery_pickings)
            self.assertEqual(
                row.get("date"),
                picking.scheduled_date.strftime(const.MAXOPTRA_DATE_FORMAT),
            )
            self.assertEqual(
                row.get("distributionCentreName"),
                self.warehouse.maxoptra_distribution_centre_name,
            )
            self.assertEqual(row.get("customerLocationName"), picking.partner_id.name)
            self.assertEqual(
                row.get("customerLocationAddress"),
                picking.partner_id._get_maxoptra_address(),
            )

    @freeze_time("2022-01-25 08:00:00")
    def test_csv_import_ship_only(self):
        self.assertEqual(self.warehouse.delivery_steps, "ship_only")
        delivery_pickings = self._create_all_delivery_orders()
        delivery_pickings.action_confirm()
        delivery_pickings.action_assign()
        shipment_planning = self._create_shipment_planning(delivery_pickings)
        shipment_planning.action_confirm()
        action_open_import_wiz = shipment_planning.action_import_maxoptra_schedule()
        maxoptra_file_path = get_resource_path(
            "shipment_planning_maxoptra", "tests", "data", "Schedules_25_01_2022.csv"
        )
        import_wiz_form = Form(
            self.env["shipment.maxoptra.schedule.import"].with_context(
                **action_open_import_wiz.get("context")
            )
        )
        with open(maxoptra_file_path, "rb") as maxoptra_file:
            import_wiz_form.maxoptra_schedule_file = base64.b64encode(
                maxoptra_file.read()
            )
            # TODO: Test invisible conditions for two steps
        import_wiz = import_wiz_form.save()
        import_wiz.action_import_schedule()
        # North bay area deliveries are grouped on Vehicle1
        batch_vehicle_1 = self.env["stock.picking.batch"].search(
            [
                ("vehicle_id", "=", self.vehicle1.id),
                ("shipment_planning_id", "=", shipment_planning.id),
            ]
        )
        # Force computation of stock.picking.batch.scheduled_date
        batch_vehicle_1._compute_scheduled_date()
        self.assertEqual(
            batch_vehicle_1.scheduled_date,
            min(batch_vehicle_1.picking_ids.mapped("scheduled_date")),
        )
        self.assertIn(self.delivery_azure, batch_vehicle_1.picking_ids)
        self.assertIn(self.delivery_jackson, batch_vehicle_1.picking_ids)
        self.assertIn(self.delivery_ready, batch_vehicle_1.picking_ids)
        self.assertIn(self.delivery_lumber, batch_vehicle_1.picking_ids)
        for delivery in batch_vehicle_1.picking_ids:
            self.assertEqual(
                delivery.scheduled_date, self.delivery_scheduled_date.get(delivery.name)
            )
            self.assertEqual(delivery.driver_id, self.driver1)
        self.assertEqual(batch_vehicle_1.driver_id, self.driver1)
        # South bay area deliveries are grouped on Vehicle3
        batch_vehicle_3 = self.env["stock.picking.batch"].search(
            [
                ("vehicle_id", "=", self.vehicle3.id),
                ("shipment_planning_id", "=", shipment_planning.id),
            ]
        )
        # Force computation of stock.picking.batch.scheduled_date
        batch_vehicle_3._compute_scheduled_date()
        self.assertEqual(
            batch_vehicle_3.scheduled_date,
            min(batch_vehicle_3.picking_ids.mapped("scheduled_date")),
        )
        self.assertEqual(
            batch_vehicle_3.scheduled_date,
            min(batch_vehicle_3.picking_ids.mapped("scheduled_date")),
        )
        self.assertIn(self.delivery_gemini, batch_vehicle_3.picking_ids)
        self.assertIn(self.delivery_deco_addict, batch_vehicle_3.picking_ids)
        for delivery in batch_vehicle_3.picking_ids:
            self.assertEqual(
                delivery.scheduled_date, self.delivery_scheduled_date.get(delivery.name)
            )
            self.assertEqual(delivery.driver_id, self.driver3)
        self.assertEqual(batch_vehicle_3.driver_id, self.driver3)

    @freeze_time("2022-01-25 08:00:00")
    def test_csv_import_pick_ship_grouped(self):
        self.warehouse.delivery_steps = "pick_ship"
        delivery_pickings = self._create_all_delivery_orders()
        # Force creation of one pick pickings per delivery order
        for pick in delivery_pickings:
            proc_group = self.env["procurement.group"].create({"name": pick.name})
            pick.write({"group_id": proc_group.id})
            pick.move_lines.write(
                {"procure_method": "make_to_order", "group_id": pick.group_id.id}
            )
        delivery_pickings.action_confirm()
        delivery_pickings.action_assign()
        shipment_planning = self._create_shipment_planning(delivery_pickings)
        shipment_planning.action_confirm()
        action_open_import_wiz = shipment_planning.action_import_maxoptra_schedule()
        maxoptra_file_path = get_resource_path(
            "shipment_planning_maxoptra", "tests", "data", "Schedules_25_01_2022.csv"
        )
        import_wiz_form = Form(
            self.env["shipment.maxoptra.schedule.import"].with_context(
                **action_open_import_wiz.get("context")
            )
        )
        pick_start_time = fields.Datetime.now() - relativedelta(hours=4)
        pick_operation_duration = 0.25
        with open(maxoptra_file_path, "rb") as maxoptra_file:
            import_wiz_form.maxoptra_schedule_file = base64.b64encode(
                maxoptra_file.read()
            )
            import_wiz_form.regroup_pick_operations = True
            import_wiz_form.reverse_order_pick_operations = True
            import_wiz_form.pick_operations_start_time = pick_start_time
            import_wiz_form.pick_operations_duration = pick_operation_duration
        import_wiz = import_wiz_form.save()
        import_wiz.action_import_schedule()
        # North bay area deliveries are grouped on Vehicle1
        delivery_batch_vehicle_1 = self.env["stock.picking.batch"].search(
            [
                ("vehicle_id", "=", self.vehicle1.id),
                ("shipment_planning_id", "=", shipment_planning.id),
            ]
        )
        self.assertEqual(self.delivery_azure.batch_id, delivery_batch_vehicle_1)
        self.assertEqual(self.delivery_jackson.batch_id, delivery_batch_vehicle_1)
        self.assertEqual(self.delivery_ready.batch_id, delivery_batch_vehicle_1)
        self.assertEqual(self.delivery_lumber.batch_id, delivery_batch_vehicle_1)
        self.assertEqual(delivery_batch_vehicle_1.driver_id, self.driver1)
        for delivery in delivery_batch_vehicle_1.picking_ids:
            self.assertEqual(delivery.driver_id, self.driver1)
        # North bay area pick pickings
        pick_pickings_vehicle_1 = self._get_previous_pickings(
            delivery_batch_vehicle_1.picking_ids
        )
        pick_batch_vehicle_1 = pick_pickings_vehicle_1.mapped("batch_id")
        self.assertEqual(len(pick_batch_vehicle_1), 1)
        self.assertFalse(pick_batch_vehicle_1.driver_id)
        self.assertEqual(
            self._get_previous_pickings(self.delivery_lumber).scheduled_date,
            pick_start_time,
        )
        self.assertEqual(
            self._get_previous_pickings(self.delivery_ready).scheduled_date,
            pick_start_time + relativedelta(minutes=15),
        )
        self.assertEqual(
            self._get_previous_pickings(self.delivery_jackson).scheduled_date,
            pick_start_time + relativedelta(minutes=30),
        )
        self.assertEqual(
            self._get_previous_pickings(self.delivery_azure).scheduled_date,
            pick_start_time + relativedelta(minutes=45),
        )
        # South bay area deliveries are grouped on Vehicle3
        delivery_batch_vehicle_3 = self.env["stock.picking.batch"].search(
            [
                ("vehicle_id", "=", self.vehicle3.id),
                ("shipment_planning_id", "=", shipment_planning.id),
            ]
        )
        self.assertEqual(self.delivery_gemini.batch_id, delivery_batch_vehicle_3)
        self.assertEqual(self.delivery_deco_addict.batch_id, delivery_batch_vehicle_3)
        self.assertEqual(delivery_batch_vehicle_3.driver_id, self.driver3)
        for delivery in delivery_batch_vehicle_3.picking_ids:
            self.assertEqual(delivery.driver_id, self.driver3)
        # South bay area pick pickings
        pick_pickings_vehicle_3 = self._get_previous_pickings(
            delivery_batch_vehicle_3.picking_ids
        )
        pick_batch_vehicle_3 = pick_pickings_vehicle_3.mapped("batch_id")
        self.assertEqual(len(pick_batch_vehicle_3), 1)
        self.assertFalse(pick_batch_vehicle_3.driver_id)
        self.assertEqual(
            self._get_previous_pickings(self.delivery_deco_addict).scheduled_date,
            pick_start_time,
        )
        self.assertEqual(
            self._get_previous_pickings(self.delivery_gemini).scheduled_date,
            pick_start_time + relativedelta(minutes=15),
        )
