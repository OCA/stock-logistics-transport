# Copyright 2022 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
from odoo import fields, models


class StockWarehouse(models.Model):

    _inherit = "stock.warehouse"

    maxoptra_distribution_centre_name = fields.Char(
        string="MaxOptra Distribution Centre Name",
        help="This value will be used as 'distributionCentreName' to be "
        "imported in MaxOptra",
    )
