# Copyright 2021 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _prepare_vehicle_values(self, move_line):
        purchase_order = self.env["purchase.order"].search([("name", "=", self.origin)])
        return {
            "name": f"{move_line.product_id.name} ({move_line.lot_id.name})",
            "model_id": move_line.product_id.model_id.id,
            "product_id": move_line.product_id.id,
            "stock_picking_id": self.picking_id.id,
            "lot_id": move_line.lot_id.id,
            "purchase_order_id": purchase_order.id,
        }
