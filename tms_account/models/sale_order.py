# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.model
    def create(self, vals):
        order = super().create(vals)
        if "order_line" in vals and order.has_tms_order:
            for line in order.order_line:
                line.analytic_distribution = line._default_analytic_distribution()
        return order

    @api.model
    def write(self, vals):
        order = super().write(vals)
        if "order_line" in vals:
            for line in self.order_line:
                line.analytic_distribution = line._default_analytic_distribution()
        return order
