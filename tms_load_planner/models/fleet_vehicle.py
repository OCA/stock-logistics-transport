# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle"

    space_ids = fields.One2many(
        "tms.vehicle.space",
        "vehicle_id",
        string="Spaces",
    )

    @api.model_create_multi
    def create(self, vals_list):
        vehicles = super().create(vals_list)
        vehicles._sync_model_spaces()
        return vehicles

    def write(self, vals):
        result = super().write(vals)
        if "model_id" in vals:
            self._sync_model_spaces()
        return result

    def _sync_model_spaces(self):
        """Give this vehicle one space for each slot on its model."""
        allocation_model = self.env["tms.trip.space.allocation"]
        space_model = self.env["tms.vehicle.space"]
        for vehicle in self:
            model_spaces = vehicle.model_id.space_ids
            existing = vehicle.space_ids
            obsolete = existing.filtered(
                lambda space, model_spaces=model_spaces: space.model_space_id
                not in model_spaces
            )
            if obsolete:
                rows = allocation_model.search(
                    [("vehicle_space_id", "in", obsolete.ids)]
                )
                booked = rows.filtered(lambda row: row.state == "booked")
                if booked:
                    raise ValidationError(
                        self.env._(
                            "Vehicle %(vehicle)s still has booked spaces.",
                            vehicle=vehicle.display_name,
                        )
                    )
                rows.unlink()
                obsolete.unlink()
            missing = model_spaces - vehicle.space_ids.model_space_id
            if not missing:
                continue
            space_model.create(
                [
                    {
                        "vehicle_id": vehicle.id,
                        "model_space_id": space.id,
                        "state": "available",
                    }
                    for space in missing
                ]
            )
