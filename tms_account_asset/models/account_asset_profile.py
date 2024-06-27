# Copyright (C) 2024 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountAssetProfile(models.Model):
    _inherit = "account.asset.profile"

    is_vehicle = fields.Boolean(
        string="Is a TMS vehicle",
        help="By marking this, if an asset with this profile is created, "
        "a vehicle will be created automatically",
    )
