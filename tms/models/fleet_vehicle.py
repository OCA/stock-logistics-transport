# Copyright (C) 2024 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle"

    tms_team_id = fields.Many2one("tms.team")

    tms_driver_id = fields.Many2one("tms.driver", string="Driver Id")

    # Operation
    operation = fields.Selection(
        [("cargo", "Cargo"), ("passenger", "Passenger")],
        string="Transport Type",
    )
    tms_equipment_type = fields.Selection(
        [
            ("power", "Power unit"),
            ("trailer", "Trailer"),
            ("dolly", "Dolly"),
        ],
        string="Equipment",
        default="power",
        required=True,
    )
    tms_location_id = fields.Many2one(
        "res.partner",
        string="Current location",
        domain="[('tms_location', '=', True)]",
    )

    # Insurance
    insurance_id = fields.Many2many("tms.insurance")

    def write(self, vals):
        teams = self.tms_team_id
        result = super().write(vals)
        if "operation" in vals or "tms_team_id" in vals:
            (teams | self.tms_team_id)._sync_stage_ids()
        return result
