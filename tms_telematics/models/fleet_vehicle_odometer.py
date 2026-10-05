# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class FleetVehicleOdometer(models.Model):
    _inherit = "fleet.vehicle.odometer"

    account_id = fields.Many2one(
        "tms.telematics.account",
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(related="account_id.company_id", store=True)
    device_id = fields.Many2one(
        "tms.telematics.device",
        ondelete="cascade",
        index=True,
    )
    external_id = fields.Char(index=True)
    event = fields.Selection(
        [
            ("position", "Position"),
            ("trip_start", "Trip start"),
            ("trip_end", "Trip end"),
            ("fill", "Fuel fill"),
        ],
    )
    position_set = fields.Boolean()
    odometer_km = fields.Float(string="Odometer (km)")
    speed = fields.Float(string="Speed (km/h)")
    speed_known = fields.Boolean()
    ignition = fields.Selection([("on", "On"), ("off", "Off")])
    fuel_liters = fields.Float(string="Fuel (L)")

    _account_external_uniq = models.Constraint(
        "unique (account_id, external_id)",
        "This reading was already imported.",
    )
