# Copyright (C) 2026 VSL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models
from odoo.exceptions import UserError


class TmsOrder(models.Model):
    _inherit = "tms.order"

    def button_start_order(self):
        # Run our critical-document check BEFORE the core mutates date_start.
        self._tms_document_check_critical()
        return super().button_start_order()

    def _tms_document_check_critical(self):
        today = fields.Date.context_today(self)
        holders = []
        if self.driver_id:
            holders.append(("tms.driver", self.driver_id))
        if self.vehicle_id:
            holders.append(("fleet.vehicle", self.vehicle_id))
        for model, holder in holders:
            expired = (
                self.env["tms.document"]
                .sudo()
                .search(
                    [
                        ("res_model", "=", model),
                        ("res_id", "=", holder.id),
                        ("critical", "=", True),
                        ("expiry_date", "<", today),
                    ]
                )
            )
            if expired:
                labels = dict(
                    expired.fields_get(allfields=["doc_type"])["doc_type"]["selection"]
                )
                names = ", ".join(
                    f"{d.name} ({labels.get(d.doc_type, d.doc_type)})" for d in expired
                )
                raise UserError(
                    self.env._(
                        "Cannot start the trip: %(holder)s has expired critical "
                        "document(s): %(docs)s",
                        holder=holder.display_name,
                        docs=names,
                    )
                )
