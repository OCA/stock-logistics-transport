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
