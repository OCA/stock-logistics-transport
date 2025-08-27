# Copyright 2025 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

{
    "name": "Printing Auto Shipment Advice",
    "version": "18.0.1.0.2",
    "author": "Camptocamp, BCIM, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/stock-logistics-transport",
    "category": "Warehouse Management",
    "data": [
        "security/ir_rule.xml",
        "views/shipment_advice.xml",
        "views/stock_warehouse.xml",
    ],
    "depends": [
        "printing_auto_stock_picking",
        "shipment_advice",
    ],
    "license": "AGPL-3",
}
