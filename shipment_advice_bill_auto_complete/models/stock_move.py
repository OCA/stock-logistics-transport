# Copyright 2024 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _group_by_purchase_line(self):
        """Return stock moves grouped by purchase order line."""
        moves_grouped = {}
        for move in self:
            moves_grouped.setdefault(move.purchase_line_id, self.env["stock.move"])
            moves_grouped[move.purchase_line_id] |= move
        return moves_grouped
