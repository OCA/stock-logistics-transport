# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def tms_map_set_coordinates(self, latitude, longitude):
        """Store a pin dropped on the partner map."""
        self.ensure_one()
        self.write(
            {
                "partner_latitude": latitude,
                "partner_longitude": longitude,
            }
        )
        return True
