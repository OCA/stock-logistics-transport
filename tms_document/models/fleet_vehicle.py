# Copyright (C) 2026 VSL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle"

    document_ids = fields.One2many(
        "tms.document", "res_id", string="Documents", compute="_compute_document_ids"
    )

    def _compute_document_ids(self):
        Doc = self.env["tms.document"]
        for rec in self:
            rec.document_ids = Doc.search(
                [("res_model", "=", "fleet.vehicle"), ("res_id", "=", rec.id)]
            )
