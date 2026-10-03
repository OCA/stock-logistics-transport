# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class FleetVehicleModel(models.Model):
    _inherit = "fleet.vehicle.model"

    vehicle_type = fields.Selection(
        selection_add=[
            ("truck", "Truck"),
            ("bus", "Bus"),
        ],
        ondelete={
            "truck": "set default",
            "bus": "set default",
        },
    )
