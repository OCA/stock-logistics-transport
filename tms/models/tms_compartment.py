# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class TmsCompartment(models.Model):
    _name = "tms.compartment"
    _description = "Trip compartment"
    _order = "name, id"

    name = fields.Char(required=True)
    order_id = fields.Many2one(
        "tms.order",
        string="Trip",
        required=True,
        ondelete="cascade",
        index=True,
    )
    capacity = fields.Integer(string="Passenger capacity", required=True)
