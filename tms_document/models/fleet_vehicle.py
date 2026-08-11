# Copyright (C) 2026 VSL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle"

    document_ids = fields.One2many(
        "tms.document",
        "res_id",
        string="Documents",
        compute="_compute_document_ids",
        inverse="_inverse_document_ids",
        readonly=False,
    )

    def _compute_document_ids(self):
        Doc = self.env["tms.document"]
        for rec in self:
            rec.document_ids = Doc.search(
                [("res_model", "=", "fleet.vehicle"), ("res_id", "=", rec.id)]
            )

    def _inverse_document_ids(self):
        for rec in self:
            for doc in rec.document_ids:
                if doc.res_model != rec._name or doc.res_id != rec.id:
                    doc.write({"res_model": rec._name, "res_id": rec.id})

    def unlink(self):
        documents = self.env["tms.document"].search(
            [("res_model", "=", "fleet.vehicle"), ("res_id", "in", self.ids)]
        )
        documents.action_archive()
        return super().unlink()
