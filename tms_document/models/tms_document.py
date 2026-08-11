# Copyright (C) 2026 VSL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class TmsDocument(models.Model):
    _name = "tms.document"
    _inherit = ["mail.thread"]
    _description = "TMS Document"
    _order = "expiry_date asc nulls last"
    _rec_name = "name"

    res_model = fields.Char(string="Holder Model", required=True, index=True)
    res_id = fields.Integer(string="Holder ID", required=True, index=True)
    res_ref = fields.Reference(
        selection="_selection_res_model",
        compute="_compute_res_ref",
        inverse="_inverse_res_ref",
        string="Holder",
    )
    doc_type = fields.Selection(
        selection="_selection_doc_type", string="Type", required=True, tracking=True
    )
    name = fields.Char(string="Reference", required=True, tracking=True)
    issue_date = fields.Date(tracking=True)
    expiry_date = fields.Date(index=True, tracking=True)
    state = fields.Selection(
        [("valid", "Valid"), ("expiring", "Expiring"), ("expired", "Expired")],
        compute="_compute_state",
        store=False,
    )
    critical = fields.Boolean(
        default=False,
        help="If checked, an expired document blocks trip start on its holder. "
        "Documents without an expiry date are never considered expired.",
        tracking=True,
    )
    file_id = fields.Many2one("ir.attachment", string="File", ondelete="set null")
    notes = fields.Text(tracking=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
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

    def _inverse_res_ref(self):
        for rec in self:
            if rec.res_ref:
                rec.res_model = rec.res_ref._name
                rec.res_id = rec.res_ref.id
            else:
                rec.res_model = False
                rec.res_id = False

    @api.constrains("res_model")
    def _check_res_model(self):
        allowed = dict(self._selection_res_model())
        for rec in self:
            if rec.res_model and rec.res_model not in allowed:
                raise ValidationError(
                    self.env._(
                        "Holder model %(model)s is not allowed. "
                        "Allowed models: %(allowed)s",
                        model=rec.res_model,
                        allowed=", ".join(allowed),
                    )
                )

    @api.depends("expiry_date")
    def _compute_state(self):
        today = fields.Date.context_today(self)
        horizon = self._get_expiry_horizon_days()
        for rec in self:
            if not rec.expiry_date:
                rec.state = "valid"
            elif rec.expiry_date < today:
                rec.state = "expired"
            elif rec.expiry_date <= today + timedelta(days=horizon):
                rec.state = "expiring"
            else:
                rec.state = "valid"

    def _get_expiry_horizon_days(self):
        try:
            return int(
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("tms.document.expiry_horizon_days", "30")
            )
        except (TypeError, ValueError):
            return 30

    @api.model
    def create_document_from_attachment(self, attachment_ids):
        """Create documents from the given attachments for the holder found
        in the context (``default_res_model`` / ``default_res_id``).
        """
        attachments = self.env["ir.attachment"].browse(attachment_ids)
        if not attachments:
            raise UserError(self.env._("No attachment was provided."))
        holder_model = self.env.context.get("default_res_model")
        holder_id = self.env.context.get("default_res_id")
        if not holder_model or not holder_id:
            raise UserError(
                self.env._(
                    "No holder (driver or vehicle) was provided for the documents."
                )
            )
        docs = self.env["tms.document"]
        for attachment in attachments:
            # Link the file to the holder so it appears under the holder's
            # chatter attachments, then reference it from the document.
            attachment.write({"res_model": holder_model, "res_id": holder_id})
            docs |= self.create(
                {
                    "name": attachment.name,
                    "doc_type": "other",
                    "file_id": attachment.id,
                    "res_model": holder_model,
                    "res_id": holder_id,
                }
            )
        return {"ids": docs.ids, "count": len(docs)}

    def action_replace_file(self, attachment_id):
        self.ensure_one()
        attachment = self.env["ir.attachment"].browse(attachment_id)
        if not attachment:
            raise UserError(self.env._("No attachment was provided."))
        attachment.write({"res_model": self.res_model, "res_id": self.res_id})
        old_file = self.file_id
        self.write({"file_id": attachment.id})
        if old_file:
            old_file.with_context(tms_document_allow_unlink=True).unlink()
        return True

    def unlink(self):
        # pylint: disable=method-required-super
        # Soft delete: archive the document and drop its file so it no longer
        # appears under the holder's Attachments, keeping the record (and its
        # chatter) available.
        files = self.file_id
        self.write({"active": False, "file_id": False})
        files.with_context(tms_document_allow_unlink=True).unlink()
        return True

    def action_soft_delete(self):
        self.unlink()
