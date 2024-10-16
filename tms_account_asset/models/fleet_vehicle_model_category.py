# Copyright (C) 2024 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class FleetVehicleModelCategory(models.Model):
    _inherit = "fleet.vehicle.model.category"

    asset_profile_id = fields.Many2one("account.asset.profile")
