# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command, fields, models


class ShipmentAdvicePlanner(models.TransientModel):

    _inherit = "shipment.advice.planner"

    shipment_planning_method = fields.Selection(
        selection_add=[("toursolver", "TourSolver")],
        ondelete={"toursolver": "cascade"},
    )
    delivery_resource_ids = fields.Many2many(
        comodel_name="toursolver.resource",
        string="Delivery resources",
        help="delivery resources to be considered in geo-optimazation",
    )
    toursolver_resource_id = fields.Many2one(
        comodel_name="toursolver.resource",
        string="Toursolver Resource",
        readonly=True,
        help="TourSolver resource to be propgated to the shipment advice in simple"
        "planning method",
    )
    toursolver_task_id = fields.Many2one(
        comodel_name="toursolver.task", string="Toursolver Task", readonly=True
    )

    def _prepare_shipment_advice_common_vals(self, picking_type):
        res = super()._prepare_shipment_advice_common_vals(picking_type)
        res.update(
            {
                "toursolver_resource_id": self.toursolver_resource_id.id,
                "toursolver_task_id": self.toursolver_task_id.id,
            }
        )
        return res

    def _plan_shipments_for_method(self):
        self.ensure_one()
        if self.shipment_planning_method != "toursolver":
            return super()._plan_shipments_for_method()
        for (
            picking_type,
            pickings_to_plan,
        ) in self._get_picking_to_plan_by_picking_type().items():
            self._init_toursolver_task(picking_type, pickings_to_plan)
        return self.env["shipment.advice"]

    def _prepare_toursolver_task_vals(self, picking_type, pickings_to_plan):
        task_model = self.env["toursolver.task"]
        backend = task_model._get_default_toursolver_backend()
        return {
            "toursolver_backend_id": backend.id,
            "warehouse_id": picking_type.warehouse_id.id,
            "dock_id": self.dock_id.id,
            "picking_ids": [Command.set(pickings_to_plan.ids)],
            "delivery_resource_ids": [Command.set(self.delivery_resource_ids.ids)],
        }

    def _init_toursolver_task(self, picking_type, pickings_to_plan):
        task_model = self.env["toursolver.task"]
        # create access is not given to any group
        return task_model.sudo().create(
            self._prepare_toursolver_task_vals(picking_type, pickings_to_plan)
        )
