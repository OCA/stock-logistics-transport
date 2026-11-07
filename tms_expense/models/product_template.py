# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    tms_spread_by_distance = fields.Boolean(
        string="Spread by distance",
        help=(
            "Split this expense across the trips driven since the previous "
            "fill, using each trip's odometer distance."
        ),
    )
