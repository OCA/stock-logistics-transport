# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.osv.expression import AND, OR


class StockPicking(models.Model):
    _inherit = "stock.picking"
    _order = (
        "toursolver_shipment_advice_rank asc, priority desc, scheduled_date asc,"
        " id desc"
    )

    toursolver_task_id = fields.Many2one(
        comodel_name="toursolver.task", readonly=True, copy=False
    )
    toursolver_shipment_advice_rank = fields.Integer(
        readonly=True,
        string="Toursolver Rank",
        help="The rank given by TourSolver to this picking in the set of planned stops"
        " of the related shipment advice",
    )

    @api.model
    def _get_compute_picking_to_plan_ids_depends(self):
        return super()._get_compute_picking_to_plan_ids_depends() + [
            "toursolver_task_id",
            "toursolver_task_id.state",
        ]

    def _compute_can_be_planned_in_shipment_advice(self):
        res = super()._compute_can_be_planned_in_shipment_advice()
        for rec in self:
            rec.can_be_planned_in_shipment_advice = (
                rec.can_be_planned_in_shipment_advice
                and (
                    not rec.toursolver_task_id
                    or rec.toursolver_task_id.state not in ("draft", "in_progress")
                )
            )
        return res

    def _search_can_be_planned_in_shipment_advice(self, operator, value):
        domain = super()._search_can_be_planned_in_shipment_advice(operator, value)
        if (operator == "=" and value) or (operator == "!=" and not value):
            extra_domain = [
                "|",
                ("toursolver_task_id", "=", False),
                ("toursolver_task_id.state", "not in", ("draft", "in_progress")),
            ]
            return AND([domain, extra_domain])
        extra_domain = [
            ("toursolver_task_id", "!=", False),
            ("toursolver_task_id.state", "in", ("draft", "in_progress")),
        ]
        return OR([domain, extra_domain])
