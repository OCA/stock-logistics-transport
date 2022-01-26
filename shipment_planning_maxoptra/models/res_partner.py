# Copyright 2022 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
from odoo import models

from ..const import MAXOPTRA_ADDRESS_FORMAT


class ResPartner(models.Model):

    _inherit = "res.partner"

    def _get_maxoptra_address(self):
        self.ensure_one()
        args = {
            "state_code": self.state_id.code or "",
            "country_name": self._get_country_name(),
        }
        for field in self._formatting_address_fields():
            args[field] = getattr(self, field) or ""
        # TODO: Add possibility to format address for MaxOptra on res.country?
        # TODO: Improve to allow automatic address recognition in Maxoptra
        return MAXOPTRA_ADDRESS_FORMAT % args
