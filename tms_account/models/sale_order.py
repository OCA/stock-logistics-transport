# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        for order, vals in zip(orders, vals_list, strict=True):
            if "order_line" in vals and order.has_tms_order:
                for line in order.order_line:
                    line.analytic_distribution = line._default_analytic_distribution()
        return orders

    def write(self, vals):
        res = super().write(vals)
        if "order_line" in vals:
            for line in self.order_line:
                line.analytic_distribution = line._default_analytic_distribution()
        return res
