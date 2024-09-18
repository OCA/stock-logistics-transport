# Copyright (C) 2024 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle"

    tms_team_id = fields.Many2one("tms.team")

    tms_driver_id = fields.Many2one("tms.driver", string="Driver")

    # Operation
    operation = fields.Selection([("cargo", "Cargo"), ("passenger", "Passenger")])

    capacity = fields.Float()
    cargo_uom_id = fields.Many2one(
        "uom.uom",
        domain="[('category_id', '=', 'Volume')]",
        default=lambda self: self._default_volume_uom_id(),
    )

    # Insurance
    insurance_id = fields.Many2many("tms.insurance")

    def _default_volume_uom_id(self):
        default_volume_uom_id = (
            self.env["ir.config_parameter"].sudo().get_param("tms.default_weight_uom")
        )

        if default_volume_uom_id:
            return self.env["uom.uom"].browse(int(default_volume_uom_id))
        else:
            return self.env.ref("uom.product_uom_cubic_meter", raise_if_not_found=False)
