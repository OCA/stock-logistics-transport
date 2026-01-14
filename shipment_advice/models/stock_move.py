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
    def search(self, domain, offset=0, limit=None, order=None, count=False):
        res = super().search(
            domain, offset=offset, limit=limit, order=order, count=count
        )
        # if this is used to count, sorting does not make sense, also if limit is set
        # at this point sorting for what?
        if (
            self.env.context.get("active_shipment_advice_id")
            and not count
            and not limit
        ):
            res = res.sorted("picking_sequence_in_shipment_advice")
        return res
