# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
from odoo import api, models


class ShipmentAdviceReport(models.AbstractModel):
    _name = "report.shipment_advice.report_shipment_advice"
    _description = "Shipment Advice Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            "doc_ids": docids,
            "doc_model": "shipment.advice",
            "docs": self.env["shipment.advice"].browse(docids),
            "get_package_levels": self._get_package_levels,
            "get_bulk_move_lines": self._get_bulk_move_lines,
        }

    def _get_package_levels(self, shipment):
        shipment.ensure_one()
        return shipment.loaded_package_level_ids.sorted(
            lambda level: level.picking_id.name
        )

    def _get_bulk_move_lines(self, shipment):
        shipment.ensure_one()
        return shipment.loaded_move_line_without_package_ids.sorted(
            lambda line: (line.move_id.picking_id.name, line.move_id.id, line.id)
        )
