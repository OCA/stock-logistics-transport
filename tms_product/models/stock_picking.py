# Copyright 2021 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    tms_vehicle_ids = fields.One2many("fleet.vehicle", "stock_picking_id")
    tms_vehicle_count = fields.Integer(compute="_compute_tms_vehicle_count")

    @api.depends("tms_vehicle_ids")
    def _compute_tms_vehicle_count(self):
        for picking in self:
            if picking.tms_vehicle_ids:
                picking.tms_vehicle_count = len(picking.tms_vehicle_ids)
            else:
                picking.tms_vehicle_count = 0

    def action_view_tms_vehicle(self):
        self.ensure_one()
        tms_vehicles = self.mapped("tms_vehicle_ids")
        return {
            "type": "ir.actions.act_window",
            "res_model": "fleet.vehicle",
            "views": [(False, "tree")],
            "domain": [("id", "in", tms_vehicles.ids)],
        }
