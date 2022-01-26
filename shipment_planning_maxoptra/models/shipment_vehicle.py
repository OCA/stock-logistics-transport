# Copyright 2022 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
from odoo import fields, models


class ShipmentVehicle(models.Model):

    _name = "shipment.vehicle"
    _description = "Vehicle to be used for shipment"

    name = fields.Char()
    maxoptra_name = fields.Char()
