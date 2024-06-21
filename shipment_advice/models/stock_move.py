# Copyright 2021 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    shipment_advice_id = fields.Many2one(
        comodel_name="shipment.advice",
        ondelete="set null",
        string="Planned shipment",
        index=True,
        copy=False,
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
        shipment_advices = res.shipment_advice_id
        for shipment_advice in shipment_advices:
            if (
                shipment_advice.shipment_type != "incoming"
                or not shipment_advice.company_id.shipment_advice_auto_validate
            ):
                continue
            shipment_advice.validate_when_fully_done()
        return res
