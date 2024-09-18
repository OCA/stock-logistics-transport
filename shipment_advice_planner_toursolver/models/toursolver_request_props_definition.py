# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ToursolverRequestPropsDefinition(models.Model):

    _name = "toursolver.request.props.definition"
    _description = "Toursolver request properties definition"

    options_definition = fields.PropertiesDefinition()
    orders_definition = fields.PropertiesDefinition()
