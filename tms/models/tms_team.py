# Copyright (C) 2024 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class TMSTeam(models.Model):
    _name = "tms.team"
    _description = "Transport Management System Team"

    def _default_stages(self):
        return self.env["tms.stage"].search([("is_default", "=", True)])

    def _compute_order_count(self):
        order_data = self.env["tms.order"].read_group(
            [
                ("tms_team_id", "in", self.ids),
                ("stage_id.is_completed", "!=", True),
            ],
            ["tms_team_id"],
            ["tms_team_id"],
        )
        result = {
            data["tms_team_id"][0]: int(data["tms_team_id_count"])
            for data in order_data
        }
        for team in self:
            team.order_count = result.get(team.id, 0)

    def _compute_driver_count(self):
        order_data = self.env["tms.driver"].read_group(
            [("tms_team_id", "in", self.ids)],
            ["tms_team_id"],
            ["tms_team_id"],
        )
        result = {
            data["tms_team_id"][0]: int(data["tms_team_id_count"])
            for data in order_data
        }
        for team in self:
            team.driver_count = result.get(team.id, 0)

    def _compute_vehicle_count(self):
        for team in self:
            team.vehicle_count = len(team.vehicle_ids)

    active = fields.Boolean(default=True)
    name = fields.Char(required=True)
    description = fields.Text()
    color = fields.Integer("Color Index")
    stage_ids = fields.Many2many(
        "tms.stage",
        "tms_order_team_stage_rel",
        "tms_team_id",
        "stage_id",
        string="Stages",
        default=_default_stages,
    )
    order_ids = fields.One2many(
        "tms.order",
        "tms_team_id",
        string="Orders",
        domain=[("stage_id.is_completed", "!=", True)],
    )
    order_count = fields.Integer(compute="_compute_order_count", string="Orders Count")
    sequence = fields.Integer(default=1, help="Used to sort teams. Lower is better.")

    vehicle_ids = fields.One2many("fleet.vehicle", "tms_team_id")
    vehicle_count = fields.Integer(
        compute="_compute_vehicle_count", string="Vehicles Count"
    )

    driver_ids = fields.One2many(
        "tms.driver",
        "tms_team_id",
    )
    driver_count = fields.Integer(
        compute="_compute_driver_count", string="Drivers Count"
    )

    crew_ids = fields.One2many("tms.crew", "tms_team_id")

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        index=True,
        default=lambda self: self.env.company,
        help="Company related to this order",
    )

    trips_todo_count = fields.Integer(
        string="Number of Trips", compute="_compute_trips_todo_count"
    )

    @api.depends("order_ids.stage_id")
    def _compute_trips_todo_count(self):
        for team in self:
            team.order_ids = self.env["tms.order"].search(
                [
                    ("tms_team_id", "=", team.id),
                    (
                        "stage_id.is_completed",
                        "!=",
                        True,
                    ),
                ]
            )
            data = self.env["tms.order"].read_group(
                [
                    ("tms_team_id", "=", team.id),
                    (
                        "stage_id.is_completed",
                        "!=",
                        True,
                    ),
                ],
                ["stage_id"],
                ["stage_id", "count(*) as count"],
            )

            team.trips_todo_count = 0

            for record in data:
                if "stage_id_count" in record:
                    team.trips_todo_count += record["stage_id_count"]

    _sql_constraints = [("name_uniq", "unique (name)", "Team name already exists!")]
