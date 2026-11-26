# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class TmsTelematicsReading(models.Model):
    _name = "tms.telematics.reading"
    _description = "Telematics Reading"
    _order = "timestamp desc, id desc"

    account_id = fields.Many2one(
        "tms.telematics.account",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(related="account_id.company_id", store=True)
    device_id = fields.Many2one(
        "tms.telematics.device",
        required=True,
        ondelete="cascade",
        index=True,
    )
    vehicle_id = fields.Many2one(related="device_id.vehicle_id", store=True)
    external_id = fields.Char(required=True, index=True)
    event = fields.Selection(
        [
            ("position", "Position"),
            ("trip_start", "Trip start"),
            ("trip_end", "Trip end"),
            ("fill", "Fuel fill"),
        ],
        required=True,
    )
    timestamp = fields.Datetime()
    latitude = fields.Float(digits=(10, 6))
    longitude = fields.Float(digits=(10, 6))
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
