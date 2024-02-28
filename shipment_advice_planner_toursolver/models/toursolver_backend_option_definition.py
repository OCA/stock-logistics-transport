# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ToursolverBackendOptionDefinition(models.Model):

    _name = "toursolver.backend.option.definition"
    _description = "Toursolver Backend Option Definition"

    backend_options_definition = fields.PropertiesDefinition()
