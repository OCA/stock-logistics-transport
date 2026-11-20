# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
from odoo import models


class ShipmentAdviceReport(models.AbstractModel):
    _inherit = "report.shipment_advice.report_shipment_advice"

    def _get_package_levels(self, shipment):
        return shipment._sort_by_partner_sequence(
            super()._get_package_levels(shipment), lambda level: level.picking_id
        )

    def _get_bulk_move_lines(self, shipment):
        return shipment._sort_by_partner_sequence(
            super()._get_bulk_move_lines(shipment), lambda line: line.move_id.picking_id
        )
