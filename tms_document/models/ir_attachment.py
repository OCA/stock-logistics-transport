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
        linked = self.filtered(lambda att: att.res_model == "tms.document")
        if linked:
            docs = self.env["tms.document"].browse(linked.mapped("res_id"))
            raise UserError(
                self.env._(
                    "The file '%(names)s' belongs to the document '%(document)s' and "
                    "cannot be deleted here. Manage the file (or archive the "
                    "document) from the document instead.",
                    names=", ".join(linked.mapped("name")),
                    document=docs.display_name,
                )
            )
        return super().unlink()
