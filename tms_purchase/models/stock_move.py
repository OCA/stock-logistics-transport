# Copyright (C) 2021 Marcel Savegnago <marcel.savegnago@escodoo.com.br>.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_purchase_line_for_vehicle(self, move_line):
        self.ensure_one()
        if self.purchase_line_id:
            return self.purchase_line_id
        if not self.origin:
            return self.env["purchase.order.line"]
        purchase_order = self.env["purchase.order"].search(
            [("name", "=", self.origin)], limit=1
        )
        if not purchase_order:
            return self.env["purchase.order.line"]
        return purchase_order.order_line.filtered(
            lambda line: line.product_id == move_line.product_id
        )[:1]

    def _prepare_vehicle_values(self, move_line):
        vals = super()._prepare_vehicle_values(move_line)
        purchase_line = self._get_purchase_line_for_vehicle(move_line)
        purchase_order = purchase_line.order_id
        if not purchase_order and self.origin:
            purchase_order = self.env["purchase.order"].search(
                [("name", "=", self.origin)], limit=1
            )
        if purchase_order:
            vals["purchase_order_id"] = purchase_order.id
            if purchase_order.date_order:
                vals["order_date"] = fields.Date.to_date(purchase_order.date_order)
        if move_line.location_dest_id:
            vals["location"] = move_line.location_dest_id.display_name
        if purchase_line:
            vals["net_car_value"] = purchase_line.price_subtotal
        return vals
