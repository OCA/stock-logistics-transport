# Copyright 2023 Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

{
    "name": "Stock Charterer",
    "summary": "Manage informations about goods which transit "
    "with containers by sea, plane, other",
    "version": "16.0.1.0.0",
    "author": "Akretion, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/stock-logistics-transport",
    "category": "Warehouse Management",
    "maintainer": ["bealdav"],
    "depends": [
        "stock",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/chartering.xml",
        "views/freight_container.xml",
        "views/partner.xml",
        "views/stock.xml",
        "views/vehicle.xml",
    ],
    "demo": [
        "data/demo.xml",
    ],
    "license": "AGPL-3",
    "installable": True,
}
