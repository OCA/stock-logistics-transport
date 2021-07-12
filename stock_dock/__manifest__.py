# Copyright 2021 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

{
    "name": "Loading Dock",
    "summary": "Manage the loading docks of your warehouse.",
    "version": "13.0.1.0.1",
    "author": "Camptocamp, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/stock-logistics-transport",
    "category": "Warehouse Management",
    "depends": ["stock"],
    "data": [
        "security/ir.model.access.csv",
        "demo/stock_dock.xml",
        "views/stock_dock.xml",
    ],
    "demo": ["demo/stock_dock.xml"],
    "license": "AGPL-3",
    "installable": True,
    "application": False,
}
