# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models
from odoo.exceptions import UserError

from .geotab_api import DEFAULT_SERVER, GeotabAPI, GeotabError


class TmsTelematicsAccount(models.Model):
    _inherit = "tms.telematics.account"

    @api.model
    def _selection_provider(self):
        return super()._selection_provider() + [("geotab", "Geotab")]

    @api.onchange("provider")
    def _onchange_provider_geotab(self):
        if self.provider == "geotab" and not self.server_url:
            self.server_url = DEFAULT_SERVER

    def _pull_geotab(self):
        try:
            return GeotabAPI(self).pull()
        except GeotabError as error:
            raise UserError(str(error)) from error
