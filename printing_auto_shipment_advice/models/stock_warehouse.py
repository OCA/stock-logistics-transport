# Copyright 2025 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from odoo import fields, models


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    shipment_advice_auto_printing_ids = fields.Many2many(
        "printing.auto",
        string="Auto Printing Configuration",
        domain=[("model", "=", "shipment.advice")],
    )
