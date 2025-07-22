# Copyright 2025 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from odoo import fields, models


class ShipmentAdvice(models.Model):
    _name = "shipment.advice"
    _inherit = ["shipment.advice", "printing.auto.mixin"]

    auto_printing_ids = fields.Many2many(
        "printing.auto", related="warehouse_id.shipment_advice_auto_printing_ids"
    )

    def _action_done(self):
        result = super()._action_done()
        self.handle_print_auto()
        return result
