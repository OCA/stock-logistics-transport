# Copyright 2024 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Stock Depot",
    "summary": """This module allows users to manage partners stock depots.""",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "Camptocamp, BCIM, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/stock-logistics-transport",
    "depends": ["stock"],
    "data": [
        "security/ir.model.access.csv",
        "views/stock_depot.xml",
    ],
}
