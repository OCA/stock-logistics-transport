# Copyright 2022 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
from odoo import fields, models


class StockPicking(models.Model):

    _inherit = "stock.picking"

    vehicle_id = fields.Many2one("shipment.vehicle")
    driver_id = fields.Many2one("res.partner")
