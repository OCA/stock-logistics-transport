# Copyright 2024 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

{
    "name": "Shipment Advice Reception Planner",
    "summary": "Plan your reception into shipment advices.",
    "version": "14.0.0.2.0",
    "author": "Camptocamp, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/stock-logistics-transport",
    "category": "Warehouse Management",
    "depends": [
        "shipment_advice",
        "purchase_stock",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/shipment_advice.xml",
        "views/stock_move.xml",
        "wizards/plan_reception_shipment.xml",
    ],
    "license": "AGPL-3",
    "installable": True,
    "application": False,
}
