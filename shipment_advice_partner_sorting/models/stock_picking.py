# Copyright 2021 Camptocamp SA
# Copyright 2024 Michael Tietz (MT Software) <mtietz@mt-software.de>
# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    shipment_advice_planned_partner_order_ids = fields.Many2many(
        comodel_name="shipment.advice.planned.partner.order",
        relation="shipment_advice_planned_partner_order_stock_picking_rel",
        column1="stock_picking_id",
        column2="shipment_advice_planned_partner_order_id",
    )
    sequence_in_shipment_advice = fields.Integer(
        compute="_compute_sequence_in_shipment_advice",
    )

    @api.depends("shipment_advice_planned_partner_order_ids.sequence")
    @api.depends_context("active_shipment_advice_id")
    def _compute_sequence_in_shipment_advice(self):
        for picking in self:
            planned_order = picking.shipment_advice_planned_partner_order_ids.filtered(
                lambda r: r.shipment_advice_id.id
                == self.env.context.get("active_shipment_advice_id")
            )
            picking.sequence_in_shipment_advice = (
                planned_order.sequence if planned_order else False
            )

    @api.model
    def _generate_order_by(self, order_spec, query):
        active_id = self.env.context.get("active_shipment_advice_id")
        order_spec = order_spec or self._order
        if not active_id or not order_spec:
            return super()._generate_order_by(order_spec, query)

        self._check_qorder(order_spec)
        parts = [part.strip().split() for part in order_spec.split(",")]
        if not any(part[0] == "sequence_in_shipment_advice" for part in parts):
            return super()._generate_order_by(order_spec, query)

        self.flush_model(["shipment_advice_planned_partner_order_ids"])
        self.env["shipment.advice.planned.partner.order"].flush_model(
            ["shipment_advice_id", "sequence", "stock_picking_ids"]
        )
        order_alias = query.left_join(
            self._table,
            "id",
            """
                SELECT rel.stock_picking_id, partner_order.shipment_advice_id,
                       MIN(partner_order.sequence) AS sequence
                FROM shipment_advice_planned_partner_order_stock_picking_rel rel
                JOIN shipment_advice_planned_partner_order partner_order
                  ON partner_order.id = rel.shipment_advice_planned_partner_order_id
                GROUP BY rel.stock_picking_id, partner_order.shipment_advice_id
            """,
            "stock_picking_id",
            "shipment_advice_sequence",
            extra='"{rhs}"."shipment_advice_id" = %s',
            extra_params=(active_id,),
        )
        order_elements = []
        for part in parts:
            if part[0] == "sequence_in_shipment_advice":
                direction = part[1].upper() if len(part) == 2 else ""
                default_sequence = 999999 if direction in ("ASC", "") else -999999
                order_elements.append(
                    f'COALESCE("{order_alias}"."sequence", {default_sequence}) {direction}'
                )
            else:
                clause = super()._generate_order_by(" ".join(part), query)
                if clause:
                    order_elements.append(clause.strip()[len("ORDER BY ") :])
        return " ORDER BY " + ", ".join(order_elements) + " "
