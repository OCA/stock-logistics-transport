# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class TmsRouteStop(models.Model):
    _name = "tms.route.stop"
    _description = "Transport Route Stop"
    _order = "sequence, id"

    route_id = fields.Many2one(
        "tms.route",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    location_id = fields.Many2one(
        "res.partner",
        required=True,
        context={"default_tms_location": True},
    )
    latitude = fields.Float(digits=(10, 7))
    longitude = fields.Float(digits=(10, 7))
