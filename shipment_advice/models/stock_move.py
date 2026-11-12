# Copyright 2021 Camptocamp SA
# Copyright 2024 Michael Tietz (MT Software) <mtietz@mt-software.de>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    shipment_advice_id = fields.Many2one(
        comodel_name="shipment.advice",
        ondelete="set null",
        string="Planned shipment",
        index=True,
        copy=False,
    )

    picking_sequence_in_shipment_advice = fields.Integer(
        compute="_compute_picking_sequence_in_shipment_advice"
    )

    @api.depends_context("active_shipment_advice_id")
    def _compute_picking_sequence_in_shipment_advice(self):
        shipment_advice_id = self.env.context.get("active_shipment_advice_id")

        for move in self:
            picking_sequence = False
            if shipment_advice_id:
                picking_sequence = move.picking_id.with_context(
                    active_shipment_advice_id=shipment_advice_id
                ).sequence_in_shipment_advice
            move.picking_sequence_in_shipment_advice = picking_sequence

    @property
    def shipment_advice_sort_key(self):
        """
        Return a tuple that can be used to sort moves in a shipment advice.
        This is used to sort the moves into the shipment advice report...
        """
        self.ensure_one()
        return (
            *self.picking_id.with_context(
                active_shipment_advice_id=self.env.context.get(
                    "active_shipment_advice_id"
                )
            ).shipment_advice_sort_key,
            self.id,
        )

    def _plan_in_shipment(self, shipment_advice):
        """Plan the moves into the given shipment advice."""
        self.shipment_advice_id = shipment_advice

    def _prepare_merge_moves_distinct_fields(self):
        res = super()._prepare_merge_moves_distinct_fields()
        # Avoid having stock move assign to different shipment merged together
        res.append("shipment_advice_id")
        return res

    def _action_done(self, cancel_backorder=False):
        res = super()._action_done(cancel_backorder=cancel_backorder)
        res.shipment_advice_id.auto_close_incoming_shipment_advices()
        return res

    def _action_cancel(self):
        res = super()._action_cancel()
        self.shipment_advice_id.auto_close_incoming_shipment_advices()
        return res

    @api.model
    def _generate_order_by(self, order_spec, query):
        active_id = self.env.context.get("active_shipment_advice_id")
        order_spec = order_spec or self._order
        if not active_id or not order_spec:
            return super()._generate_order_by(order_spec, query)

        self._check_qorder(order_spec)
        parts = [part.strip().split() for part in order_spec.split(",")]
        if not any(part[0] == "picking_sequence_in_shipment_advice" for part in parts):
            return super()._generate_order_by(order_spec, query)

        self.env["shipment.advice.planned.partner.order"].flush_model(
            ["shipment_advice_id", "sequence", "stock_picking_ids"]
        )
        # we join on a subquery that calculates the sequence
        # associated to the active shipment advice for the partner's
        # picking
        order_alias = query.left_join(
            self._table,
            "picking_id",
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
        # we mimic the behaviour of native odoo by constructing the ORDER BY clause manually
        # and process only the parts relevant to picking_sequence_in_shipment_advice.
        # Other parts are delegated to the super method.
        for part in parts:
            if part[0] == "picking_sequence_in_shipment_advice":
                direction = part[1].upper() if len(part) == 2 else ""
                # always put moves not linked to the active shipment advice at the end
                default_sequence = 999999 if direction in ("ASC", "") else -999999
                order_elements.append(
                    f'COALESCE("{order_alias}"."sequence", {default_sequence}) {direction}'
                )
            else:
                clause = super()._generate_order_by(" ".join(part), query)
                if clause:
                    order_elements.append(clause.strip()[len("ORDER BY ") :])
        return " ORDER BY " + ", ".join(order_elements) + " "
