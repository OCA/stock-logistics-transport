# Copyright (C) 2024 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class TMSCrew(models.Model):
    _name = "tms.crew"
    _description = "Transport Management System Crew"

    # _inherit = ["mail.thread", "mail.activity.mixin"]

    active = fields.Boolean(default=True)
    name = fields.Char(required=True)
    description = fields.Text()

    driver_ids = fields.Many2many(
        "tms.driver",
        "tms_crew_drivers_rel",
        string="Drivers",
        required=True,
    )
    personnel_ids = fields.Many2many(
        "res.partner",
        "tms_crew_personnel_rel",
        string="Other Personnel",
    )
    default_vehicle_id = fields.Many2one("fleet.vehicle", string="Default Vehicle")

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        index=True,
        default=lambda self: self.env.company,
        help="Company related to this order",
    )

    tms_team_id = fields.Many2one("tms.team")

    _sql_constraints = [("name_uniq", "unique (name)", "Crew name already exists!")]
