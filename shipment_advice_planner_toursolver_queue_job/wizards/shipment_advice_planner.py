# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class ShipmentAdvicePlanner(models.TransientModel):

    _inherit = "shipment.advice.planner"

    def _init_toursolver_task(self, warehouse, pickings_to_plan):
        task = super()._init_toursolver_task(warehouse, pickings_to_plan)
        task._toursolver_process()
        return task
