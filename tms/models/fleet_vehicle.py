# Copyright (C) 2024 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle"

    tms_team_id = fields.Many2one("tms.team")

    tms_driver_id = fields.Many2one("tms.driver", string="Driver Id")

    # Operation
    operation = fields.Selection([("cargo", "Cargo"), ("passenger", "Passenger")])
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

    capacity = fields.Float(string="Volume capacity")
    cargo_uom_id = fields.Many2one(
        "uom.uom",
        string="Volume unit",
        domain=lambda self: self.env["res.config.settings"]._volume_domain(),
        default=lambda self: self._default_volume_uom_id(),
    )
    weight_capacity = fields.Float(string="Payload")
    weight_uom_id = fields.Many2one(
        "uom.uom",
        string="Weight unit",
        domain=lambda self: self.env["res.config.settings"]._weight_domain(),
        default=lambda self: self._default_weight_uom_id(),
    )

    # Insurance
    insurance_id = fields.Many2many("tms.insurance")

    def _default_volume_uom_id(self):
        return self.env["res.config.settings"]._configured_uom(
            "tms.default_volume_uom", "uom.product_uom_cubic_meter"
        )

    def _default_weight_uom_id(self):
        return self.env["res.config.settings"]._configured_uom(
            "tms.default_weight_uom", "uom.product_uom_kgm"
        )

    def write(self, vals):
        teams = self.tms_team_id
        result = super().write(vals)
        if "operation" in vals or "tms_team_id" in vals:
            (teams | self.tms_team_id)._sync_stage_ids()
        return result
