# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    can_be_planned_in_shipment_advice = fields.Boolean(
        compute="_compute_can_be_planned_in_shipment_advice",
        search="_search_can_be_planned_in_shipment_advice",
    )

    @api.model
    def _get_compute_picking_to_plan_ids_depends(self):
        return ["planned_shipment_advice_id", "state", "picking_type_code"]

    @api.depends(lambda m: m._get_compute_picking_to_plan_ids_depends())
    def _compute_can_be_planned_in_shipment_advice(self):
        for rec in self:
            rec.can_be_planned_in_shipment_advice = (
                not rec.planned_shipment_advice_id
                and rec.state == "assigned"
                and rec.picking_type_code == "outgoing"
            )

    def _search_can_be_planned_in_shipment_advice(self, operator, value):
        if (operator == "=" and value) or (operator == "!=" and not value):
            return [
                ("planned_shipment_advice_id", "=", False),
                ("state", "=", "assigned"),
                ("picking_type_code", "=", "outgoing"),
            ]
        return [
            "|",
            "|",
            ("planned_shipment_advice_id", "!=", False),
            ("state", "!=", "assigned"),
            ("picking_type_code", "!=", "outgoing"),
        ]

    def init(self):
        self.env.cr.execute(
            """
                CREATE INDEX IF NOT EXISTS
                stock_picking_can_be_planned_in_shipment_advice_index
                ON stock_picking(can_be_planned_in_shipment_advice)
                WHERE can_be_planned_in_shipment_advice is true;
            """
        )
