# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ShipmentAdvice(models.Model):

    _inherit = "shipment.advice"

    toursolver_resource_id = fields.Many2one(
        comodel_name="toursolver.resource", string="Toursolver Resource", readonly=True
    )
    toursolver_task_id = fields.Many2one(
        comodel_name="toursolver.task", string="Toursolver Task", readonly=True
    )
