# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from datetime import datetime, timedelta

import pytz

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class ShipmentAdvice(models.Model):

    _inherit = "shipment.advice"

    toursolver_resource_id = fields.Many2one(
        comodel_name="toursolver.resource",
        string="Toursolver Resource",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    toursolver_task_id = fields.Many2one(
        comodel_name="toursolver.task", string="Toursolver Task", readonly=True
    )
    # Toursolver stats
    toursolver_nbr_tours = fields.Integer(
        string="Number of Tours", compute="_compute_toursolver_stats", store=True
    )
    toursolver_nbr_visits = fields.Integer(
        string="Number of visits",
        compute="_compute_toursolver_stats",
        store=True,
        help="Number of delivery stops in the tours",
    )
    toursolver_delivery_cost = fields.Float(
        compute="_compute_toursolver_stats", store=True
    )
    toursolver_additional_cost = fields.Float(
        compute="_compute_toursolver_stats", store=True
    )
    toursolver_total_cost = fields.Float(
        compute="_compute_toursolver_stats", store=True
    )
    toursolver_travel_distance = fields.Float(
        compute="_compute_toursolver_stats",
        store=True,
        help="Distance to travel for the delivery in Km",
    )
    toursolver_travel_distance_uom = fields.Many2one(
        "uom.uom",
        string="Distance UoM",
        default=lambda d: d.env.ref("uom.product_uom_km").id,
        readonly=True,
    )
    toursolver_travel_distance_uom_name = fields.Char(
        string="Distance unit of measure label",
        related="toursolver_travel_distance_uom.name",
        readonly=True,
    )

    toursolver_travel_duration = fields.Float(
        compute="_compute_toursolver_stats",
        store=True,
        help="Driving time for the travel, excluding the time spent at each stop",
    )
    toursolver_travel_start_dt = fields.Datetime(
        string="Travel Start Time", compute="_compute_toursolver_stats", store=True
    )
    toursolver_travel_end_dt = fields.Datetime(
        string="Travel End Time", compute="_compute_toursolver_stats", store=True
    )
    toursolver_travel_total_time = fields.Float(
        compute="_compute_toursolver_stats",
        store=True,
        help="Total time for the travel, including the time spent at each stop and "
        "reloading time",
    )
    is_create_toursolver_task_allowed = fields.Boolean(
        compute="_compute_is_create_toursolver_task_allowed"
    )

    @api.depends("state", "toursolver_task_id")
    def _compute_is_create_toursolver_task_allowed(self):
        for rec in self:
            rec.is_create_toursolver_task_allowed = (
                rec.state not in ("draft", "done", "cancel")
                and not rec.toursolver_task_id
            )

    def create_toursolver_task(self):
        self.ensure_one()
        if not self.is_create_toursolver_task_allowed:
            raise UserError(_("You can't recreate the toursolver task."))
        task_model = self.env["toursolver.task"]
        backend = task_model._get_default_toursolver_backend()
        task_model.sudo().create(
            {
                "shipment_advice_ids": [Command.set(self.ids)],
                "toursolver_backend_id": backend.id,
                "warehouse_id": self.warehouse_id.id,
                "dock_id": self.dock_id.id,
                "picking_ids": [Command.set(self.planned_picking_ids.ids)],
                "delivery_resource_ids": [Command.set(self.toursolver_resource_id.ids)],
            }
        )

    @api.depends(
        "toursolver_task_id",
        "toursolver_resource_id",
        "toursolver_task_id.state",
        "toursolver_task_id.result_data",
    )
    def _compute_toursolver_stats(self):
        for record in self:
            task = record.toursolver_task_id
            record._reset_stats()
            if task.state == "done":
                record._collect_toursolver_stats()

    def _reset_stats(self):
        self.ensure_one()
        self.toursolver_nbr_tours = 0
        self.toursolver_nbr_visits = 0
        self.toursolver_delivery_cost = 0.0
        self.toursolver_additional_cost = 0.0
        self.toursolver_total_cost = 0.0
        self.toursolver_travel_distance = 0.0
        self.toursolver_travel_duration = 0.0
        self.toursolver_travel_start_dt = False
        self.toursolver_travel_end_dt = False
        self.toursolver_travel_total_time = 0.0

    def _collect_toursolver_stats(self):
        self.ensure_one()
        task = self.toursolver_task_id
        json = task.result_json
        if not json or "tours" not in json:
            # No tours in the result, nothing to do since it's an old
            # result format prior to the introduction of these stats fields
            return
        tours = [
            tour
            for tour in json["tours"]
            if tour["resourceId"] == self.toursolver_resource_id.resource_id
        ]
        self.toursolver_nbr_tours = len(tours)
        for tour in tours:
            for i in tour["plannedOrders"]:
                stop_type = i.get("stopType")
                if stop_type == 0:  # we only count delivery stops
                    self.toursolver_nbr_visits += 1
                elif stop_type == 1:  # start of the tour
                    start_time = i.get("stopStartTime")
                    day_id = i.get("dayId")
                    self.toursolver_travel_start_dt = self._stop_start_time_to_dt(
                        start_time, day_id
                    )
                elif stop_type == 2:  # end of the tour
                    start_time = i.get("stopStartTime")
                    day_id = i.get("dayId")
                    self.toursolver_travel_end_dt = self._stop_start_time_to_dt(
                        start_time, day_id
                    )
            self.toursolver_delivery_cost += tour["deliveryCost"]
            self.toursolver_additional_cost += tour["additionalCost"]
            self.toursolver_total_cost += tour["totalCost"]
            self.toursolver_travel_distance += tour["travelDistance"]
            duration = tour["travelDuration"]
            # duration is expressed as "HH:MM:SS" in the result
            # we convert it to a float representing the number of minutes
            duration_parts = duration.split(":")
            hours = int(duration_parts[0])
            minutes = int(duration_parts[1])
            self.toursolver_travel_duration += hours + minutes / 60
        self.toursolver_travel_total_time = (
            self.toursolver_travel_end_dt - self.toursolver_travel_start_dt
        ).total_seconds() / 3600
        if self.toursolver_travel_distance:
            self.toursolver_travel_distance = self.toursolver_travel_distance / 1000

    def _stop_start_time_to_dt(self, start_time, day_id):
        self.ensure_one()
        fmt = "%H:%M:%S"
        parts = start_time.split(":")
        if len(parts) == 2:
            fmt = "%H:%M"
        time_obj = datetime.strptime(start_time, fmt)
        tz_name = self.env.context.get("tz") or self.env.user.tz
        if not tz_name:
            raise UserError(
                _("Please configure your timezone in your user preferences")
            )
        local_tz = pytz.timezone(tz_name)
        local_dt = datetime.combine(self.toursolver_task_id.date, time_obj.time())
        local_dt = local_dt + timedelta(days=int(day_id) - 1)
        local_dt = local_tz.localize(local_dt)
        utc_dt = local_dt.astimezone(pytz.utc)
        # convert to naive datetime
        return utc_dt.replace(tzinfo=None)
