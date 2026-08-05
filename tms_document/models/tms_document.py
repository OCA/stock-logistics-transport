# Copyright (C) 2026 VSL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import timedelta

from odoo import api, fields, models


class TmsDocument(models.Model):
    _name = "tms.document"
    _description = "TMS Document"
    _order = "expiry_date asc nulls last"
    _rec_name = "name"

    res_model = fields.Char(string="Holder Model", required=True, index=True)
    res_id = fields.Integer(string="Holder ID", required=True, index=True)
    res_ref = fields.Reference(
        selection="_selection_res_model", compute="_compute_res_ref", string="Holder"
    )
    doc_type = fields.Selection(
        selection="_selection_doc_type", string="Type", required=True
    )
    name = fields.Char(string="Reference", required=True)
    issue_date = fields.Date()
    expiry_date = fields.Date(index=True)
    state = fields.Selection(
        [("valid", "Valid"), ("expiring", "Expiring"), ("expired", "Expired")],
        compute="_compute_state",
        string="State",
        store=False,
    )
    critical = fields.Boolean(
        default=False,
        help="If checked, an expired document blocks trip start on its holder.",
    )
    datas = fields.Binary(string="File", attachment=True)
    notes = fields.Text()
    company_id = fields.Many2one(
        "res.company", string="Company",
        default=lambda self: self.env.company, required=True,
    )
    active = fields.Boolean(default=True)

    def _selection_res_model(self):
        return [("tms.driver", "Driver"), ("fleet.vehicle", "Vehicle")]

    def _selection_doc_type(self):
        return [
            ("license", "Driving License"),
            ("insurance", "Insurance"),
            ("inspection", "Vehicle Inspection"),
            ("other", "Other"),
        ]

    @api.depends("res_model", "res_id")
    def _compute_res_ref(self):
        for rec in self:
            if rec.res_model and rec.res_id and rec.res_model in self.env:
                rec.res_ref = f"{rec.res_model},{rec.res_id}"
            else:
                rec.res_ref = False

    @api.depends("expiry_date")
    def _compute_state(self):
        today = fields.Date.context_today(self)
        horizon = self._get_expiry_horizon_days()
        for rec in self:
            if not rec.expiry_date:
                rec.state = "valid"
            elif rec.expiry_date < today:
                rec.state = "expired"
            elif rec.expiry_date < today + timedelta(days=horizon):
                rec.state = "expiring"
            else:
                rec.state = "valid"

    def _get_expiry_horizon_days(self):
        return int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("tms.document.expiry_horizon_days", "30")
        )
