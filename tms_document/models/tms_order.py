# Copyright (C) 2026 VSL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models
from odoo.exceptions import UserError


class TmsOrder(models.Model):
    _inherit = "tms.order"

    def button_start_order(self):
        # Run our critical-document check BEFORE the core mutates date_start.
        # This coexists with the core inline checks for driver license and
        # vehicle insurance expiry (tms.default_driver_license_security_days
        # and tms.default_vehicle_insurance_security_days).  Both checks run;
        # the core checks cover the legacy driver/vehicle fields, while this
        # covers the generic tms.document framework.
        self._tms_document_check_critical()
        return super().button_start_order()

    def _tms_document_check_critical(self):
        today = fields.Date.context_today(self)
        for order in self:
            holders = []
            if order.driver_id:
                holders.append(("tms.driver", order.driver_id))
            if order.vehicle_id:
                holders.append(("fleet.vehicle", order.vehicle_id))
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
                        expired.fields_get(allfields=["doc_type"])["doc_type"][
                            "selection"
                        ]
                    )
                    names = ", ".join(
                        f"{d.name} ({labels.get(d.doc_type, d.doc_type)})"
                        for d in expired
                    )
                    raise UserError(
                        self.env._(
                            "Cannot start the trip: %(holder)s has expired critical "
                            "document(s): %(docs)s",
                            holder=holder.display_name,
                            docs=names,
                        )
                    )
