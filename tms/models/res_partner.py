# Copyright (C) 2018 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models

LOCATION_TYPES = [("terrestrial", "Terrestrial")]


class ResPartner(models.Model):
    _inherit = "res.partner"
    # # TMS Type
    tms_location = fields.Boolean(string="Transport location")

    # Location - Types
    location_type = fields.Selection(selection=LOCATION_TYPES)
