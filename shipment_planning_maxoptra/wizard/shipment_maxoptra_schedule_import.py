# Copyright 2022 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
import base64
import codecs
import csv
import io
from datetime import datetime

import pytz
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import format_duration

from odoo.addons.base.models.res_partner import _tz_get

from ..const import MAXOPTRA_DATETIME_FORMAT

# Copied from odoo.tools.pycompat to use with DictReader
_reader = codecs.getreader("utf-8")


class ShipmentMaxoptraScheduleImport(models.TransientModel):

    _name = "shipment.maxoptra.schedule.import"
    _description = "Import maxoptra schedule and create batch pickings"

    @api.model
    def _default_tz(self):
        # TODO: Check if must use tz from warehouse in default_get instead?
        return self.env.context.get("tz")

    maxoptra_schedule_file = fields.Binary(attachment=False, required=True)
    maxoptra_schedule_file_name = fields.Char()
    shipment_planning_id = fields.Many2one("shipment.planning")
    warehouse_delivery_steps = fields.Selection(
        related="shipment_planning_id.warehouse_id.delivery_steps"
    )
    tz = fields.Selection(
        _tz_get,
        string="Timezone",
        default=lambda s: s._default_tz(),
        help="Timezone for datetime in CSV. Leave empty if UTC",
    )

    regroup_pick_operations = fields.Boolean(
        help="Create a batch picking for all the pick operations assigned to a batch delivery"
    )
    reverse_order_pick_operations = fields.Boolean(
        help="Schedule the pick operations in the reverse order of the following operations"
    )
    pick_operations_start_time = fields.Datetime(
        help="Start time for the first planned pick operation. "
        "Leave empty to avoid rescheduling."
    )
    pick_operations_duration = fields.Float(help="Duration between each pick operation")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get("active_model") != "shipment.planning":
            raise UserError(
                _("This wizard can only be called from shipment planning objects.")
            )
        shipment_planning_id = self.env.context.get("active_id")
        if "shipment_planning_id" in fields_list and not res.get(
            "shipment_planning_id"
        ):
            res["shipment_planning_id"] = shipment_planning_id
        return res

    # TODO Add constraints according to warehouse delivery steps?

    def action_import_schedule(self):
        self.ensure_one()
        maxoptra_schedule = self.read_csv()
        schedule_by_vehicles = self.group_schedule_by_vehicle(maxoptra_schedule)
        delivery_batch_pickings = self.create_delivery_batch_picking_by_vehicle(
            schedule_by_vehicles
        )
        if self.warehouse_delivery_steps == "pick_ship":
            if self.regroup_pick_operations:
                self.regroup_operations(
                    delivery_batch_pickings,
                    self.reverse_order_pick_operations,
                    self.pick_operations_start_time,
                    self.pick_operations_duration,
                )
        elif self.warehouse_delivery_steps == "pick_pack_ship":
            raise UserError(
                _(
                    "Scheduling of operations from Maxoptra in Pick-Pack-Ship "
                    "is not implemented yet."
                )
            )
        self.update_shipment_planning(delivery_batch_pickings)

    def regroup_operations(
        self,
        following_batch_pickings,
        reverse_order=False,
        start_datetime=False,
        operation_duration=False,
    ):
        new_batch_picking_ids = []
        scheduled_picking_ids = []
        for batch_picking in following_batch_pickings:
            cnt = 0
            new_batch = self.env["stock.picking.batch"].create({})
            # FIXME: If previous_picking have different source location, the
            #  assignation to the batch will fail, and we should either create
            #  one batch per source location or ignore some.
            for picking in batch_picking.picking_ids.sorted(
                "scheduled_date", reverse_order
            ):
                picking_moves = picking.move_lines
                previous_moves = picking_moves.move_orig_ids
                previous_pickings = previous_moves.picking_id
                for pick in previous_pickings:
                    # Avoid rescheduling same picking multiple times
                    if pick.id in scheduled_picking_ids:
                        continue
                    pick_values = {"batch_id": new_batch.id}
                    if start_datetime and operation_duration:
                        hours, minutes = format_duration(operation_duration).split(":")
                        delay = relativedelta(
                            hours=cnt * int(hours), minutes=cnt * int(minutes)
                        )
                        pick_values["scheduled_date"] = start_datetime + delay
                    pick.write(pick_values)
                    # increment counter manually as we cannot use enumerate
                    #  on the two nested loops
                    cnt += 1
            new_batch_picking_ids.append(new_batch.id)
        return self.env["stock.picking.batch"].browse(new_batch_picking_ids)

    def create_delivery_batch_picking_by_vehicle(self, schedule_by_vehicles):
        batch_ids = []
        for vehicle_name, maxoptra_deliveries in schedule_by_vehicles.items():
            batch_picking_values = self._prepare_batch_picking_values(vehicle_name)
            batch_picking = self.env["stock.picking.batch"].create(batch_picking_values)
            batch_ids.append(batch_picking.id)
            for maxoptra_delivery in maxoptra_deliveries:
                picking = self.env["stock.picking"].search(
                    [("name", "=", maxoptra_delivery.get("picking_name"))]
                )
                # TODO: Add more checks?
                if not picking:
                    raise UserError(
                        _("No matching picking found for Order reference %s")
                        % maxoptra_delivery.get("picking_name")
                    )
                picking.write(
                    {
                        "batch_id": batch_picking.id,
                        "scheduled_date": maxoptra_delivery.get(
                            "scheduled_delivery_start_datetime"
                        ),
                        "vehicle_id": batch_picking.vehicle_id.id,
                    }
                )
        return self.env["stock.picking.batch"].browse(batch_ids)

    def _prepare_batch_picking_values(self, vehicle_name):
        vehicle = self.env["shipment.vehicle"].search([("name", "=", vehicle_name)])
        values = {
            "company_id": self.shipment_planning_id.company_id.id,
            "vehicle_id": vehicle.id,
        }
        return values

    def group_schedule_by_vehicle(self, maxoptra_schedule):
        res = {}
        for maxoptra_delivery in maxoptra_schedule:
            res.setdefault(maxoptra_delivery.get("vehicle"), []).append(
                maxoptra_delivery
            )
        return res

    def update_shipment_planning(self, batch_pickings):
        values = {
            "maxoptra_exported_file": self.maxoptra_schedule_file,
            "maxoptra_exported_file_name": self.maxoptra_schedule_file_name,
        }
        if batch_pickings:
            values["batch_picking_ids"] = [(6, 0, batch_pickings.ids)]
        self.shipment_planning_id.write(values)
        return True

    def read_csv(self):
        res = []
        csv_data = base64.b64decode(self.maxoptra_schedule_file)
        buff = io.BytesIO(csv_data)
        reader = csv.DictReader(_reader(buff))
        for row in reader:
            # TODO: Allow to use different CSV column?
            delivery_start = datetime.strptime(
                row.get("Scheduled arrival time"), MAXOPTRA_DATETIME_FORMAT
            )
            if self.tz:
                timezone = pytz.timezone(self.tz)
                utc = pytz.utc
                delivery_start = (
                    timezone.localize(delivery_start)
                    .astimezone(utc)
                    .replace(tzinfo=None)
                )
            res.append(
                {
                    "picking_name": row.get("Order reference"),
                    "picking_scheduled_seq": row.get("Scheduled sequence"),
                    "driver": row.get("Performer name"),
                    "vehicle": row.get("Vehicle name"),
                    "scheduled_delivery_start_datetime": delivery_start,
                }
            )
        buff.close()
        return res
