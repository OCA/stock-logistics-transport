# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle"

    tms_last_latitude = fields.Float(
        string="Last latitude",
        digits=(10, 7),
        compute="_compute_tms_last_position",
    )
    tms_last_longitude = fields.Float(
        string="Last longitude",
        digits=(10, 7),
        compute="_compute_tms_last_position",
    )
    tms_motion = fields.Selection(
        [
            ("moving", "On, moving"),
            ("idle", "On, stopped"),
            ("off", "Off"),
        ],
        string="Telematics status",
        compute="_compute_tms_last_position",
    )
    tms_map_mode = fields.Selection(
        [
            ("air", "Air"),
            ("water", "Water"),
            ("road", "Road"),
            ("rail", "Rail"),
        ],
        string="Map icon",
        compute="_compute_tms_map_mode",
    )
    tms_trip_count = fields.Integer(compute="_compute_tms_trip_count")
    tms_vehicle_group_ids = fields.Many2many(
        comodel_name="tms.vehicle.group",
        relation="tms_vehicle_group_vehicle_rel",
        column1="vehicle_id",
        column2="group_id",
        string="Vehicle Groups",
        groups="tms_map.group_tms_vehicle_group",
    )

    @api.depends("model_id.vehicle_type", "model_id.category_id.name")
    def _compute_tms_map_mode(self):
        order = self.env["tms.order"]
        for vehicle in self:
            vehicle.tms_map_mode = order._map_mode_for_vehicle(vehicle)

    def _compute_tms_trip_count(self):
        grouped = self.env["tms.order"]._read_group(
            [("vehicle_id", "in", self.ids)],
            ["vehicle_id"],
            ["__count"],
        )
        counts = {vehicle.id: count for vehicle, count in grouped if vehicle}
        for record in self:
            record.tms_trip_count = counts.get(record.id, 0)

    def _compute_tms_last_position(self):
        positions = {
            row["id"]: row
            for row in self.env["tms.order"].tms_map_vehicle_positions(self.ids)
        }
        for vehicle in self:
            position = positions.get(vehicle.id)
            vehicle.tms_last_latitude = position["latitude"] if position else 0.0
            vehicle.tms_last_longitude = position["longitude"] if position else 0.0
            vehicle.tms_motion = position["motion"] if position else "off"
