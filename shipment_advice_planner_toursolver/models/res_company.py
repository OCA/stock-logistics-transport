# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):

    _inherit = "res.company"

    toursolver_backend_id = fields.Many2one(
        comodel_name="toursolver.backend", string="TourSolver Backend"
    )
