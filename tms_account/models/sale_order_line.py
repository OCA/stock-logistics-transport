# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models
from odoo.fields import Command


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _prepare_invoice_line(self, **optional_values):
        """Prepare the values to create the new invoice line for a sales order line.

        :param optional_values: any parameter that
        should be added to the returned invoice line
        :rtype: dict
        """
        self.ensure_one()
        res = {
            "display_type": self.display_type or "product",
            "sequence": self.sequence,
            "name": self.name,
            "product_id": self.product_id.id,
            "product_uom_id": self.product_uom.id,
            "quantity": self.qty_to_invoice,
            "discount": self.discount,
            "price_unit": self.price_unit,
            "tax_ids": [Command.set(self.tax_id.ids)],
            "sale_line_ids": [Command.link(self.id)],
            "is_downpayment": self.is_downpayment,
            "tms_factor": self.tms_factor,
            "tms_factor_uom": self.tms_factor_uom,
        }
        self._set_analytic_distribution(res, **optional_values)
        if optional_values:
            res.update(optional_values)
        if self.display_type:
            res["account_id"] = False
        return res
