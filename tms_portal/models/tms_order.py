# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models
from odoo.exceptions import AccessError, UserError


class TMSOrder(models.Model):
    _inherit = "tms.order"

    def _check_driver_pickup(self, parent):
        self.ensure_one()
        self.check_access("read")
        parent.check_access("read")
        if parent.order_id != self or parent.parent_id:
            raise UserError(
                self.env._("Record the pickup on the sold cargo of this trip.")
            )
        if self.driver_id.partner_id != self.env.user.partner_id:
            raise AccessError(self.env._("This trip is assigned to another driver."))

    def add_pickup(self, parent, values):
        """Add a pickup line for the portal driver assigned to this trip."""
        self.ensure_one()
        self._check_driver_pickup(parent)
        return (
            self.env["tms.cargo"]
            .sudo()
            .create(
                {
                    "parent_id": parent.id,
                    "order_id": self.id,
                    "name": values.get("name") or parent.name,
                    "quantity": values.get("quantity") or 0.0,
                    "uom_id": parent.uom_id.id,
                    "weight": values.get("weight") or 0.0,
                    "weight_uom_id": parent.weight_uom_id.id,
                    "volume": values.get("volume") or 0.0,
                    "volume_uom_id": parent.volume_uom_id.id,
                    "state": "loaded",
                }
            )
        )
