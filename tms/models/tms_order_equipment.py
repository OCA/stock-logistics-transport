# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class TMSOrderEquipment(models.Model):
    _name = "tms.order.equipment"
    _description = "Trailer or dolly coupled to a trip"
    _order = "id"

    order_id = fields.Many2one("tms.order", required=True, ondelete="cascade")
    vehicle_id = fields.Many2one(
        "fleet.vehicle",
        string="Equipment",
        required=True,
        domain="[('tms_equipment_type', 'in', ('trailer', 'dolly'))]",
    )
    role = fields.Selection(
        related="vehicle_id.tms_equipment_type",
        store=True,
    )
    dropped = fields.Boolean()
    drop_location_id = fields.Many2one(
        "res.partner",
        string="Drop location",
        domain="[('tms_location', '=', True)]",
    )
    drop_date = fields.Datetime(readonly=True)

    @api.constrains("vehicle_id")
    def _check_equipment_type(self):
        for line in self:
            if line.vehicle_id.tms_equipment_type not in ("trailer", "dolly"):
                raise ValidationError(
                    self.env._("A convoy line is a trailer or a dolly.")
                )

    def action_drop(self):
        for line in self:
            if line.role != "trailer":
                raise UserError(self.env._("Only a trailer can be dropped."))
            if line.dropped:
                continue
            location = line.drop_location_id or line.order_id.destination_id
            if not location:
                raise UserError(
                    self.env._("Set the location where the trailer is dropped.")
                )
            line.write(
                {
                    "dropped": True,
                    "drop_location_id": location.id,
                    "drop_date": fields.Datetime.now(),
                }
            )
            line.vehicle_id.tms_location_id = location
