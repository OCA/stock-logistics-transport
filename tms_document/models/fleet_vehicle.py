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

    def action_add_document(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "tms_document.action_tms_document_new"
        )
        action["context"] = {
            "default_res_model": "fleet.vehicle",
            "default_res_id": self.id,
        }
        return action
