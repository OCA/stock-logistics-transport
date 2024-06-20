# Copyright 2024 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import models


class WizardUnplanShipment(models.TransientModel):
    _inherit = "wizard.unplan.shipment"

    def action_unplan(self):
        incoming_moves = self.move_ids.filtered(
            lambda move: move.shipment_advice_id.shipment_type == "incoming"
        )
        res = super().action_unplan()
        # When moves are added through the reception planner, their quantity may have been split
        # So merge them back if possible
        incoming_moves._merge_moves()
        return res
