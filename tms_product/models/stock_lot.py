# Copyright 2021 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models


class StockLot(models.Model):
    _inherit = "stock.lot"

    vehicle_id = fields.Many2one("fleet.vehicle", readonly=True)

    def action_view_vehicle(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "fleet.vehicle",
            "view_mode": "form",
            "res_id": self.vehicle_id.id,
            "target": "current",
            "name": _("Vehicle for Lot/Serial Number: %s") % self.name,
        }
