# Copyright (C) 2026 VSL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models
from odoo.exceptions import UserError


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    def unlink(self):
        # pylint: disable=no-raise-unlink
        # Intentional: deleting a document's file from the attachments panel
        # would silently break the document, so we warn and block it instead.
        # The tms_document.unlink (soft delete) bypasses this via context to
        # drop the file when the document is archived.
        if self.env.context.get("tms_document_allow_unlink"):
            return super().unlink()
        linked_docs = self.env["tms.document"].search([("file_id", "in", self.ids)])
        protected = self.filtered(
            lambda att: (
                att.res_model == "tms.document" or att.id in linked_docs.file_id.ids
            )
        )
        if protected:
            docs = linked_docs | self.env["tms.document"].search(
                [("file_id", "in", protected.ids)]
            )
            raise UserError(
                self.env._(
                    "The file '%(names)s' belongs to the document '%(document)s' and "
                    "cannot be deleted here. Manage the file (or archive the "
                    "document) from the document instead.",
                    names=", ".join(protected.mapped("name")),
                    document=", ".join(docs.mapped("display_name")),
                )
            )
        return super().unlink()
