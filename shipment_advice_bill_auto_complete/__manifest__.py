# Copyright 2024 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{
    "name": "Shipment Advice Bill Auto Complete",
    "summary": "Generate vendor bill lines for incoming shipment advice",
    "version": "14.0.1.3.0",
    "category": "Invoicing Management",
    "author": "Camptocamp, Odoo Community Association (OCA)",
    "maintainers": ["TDu", "jbaudoux"],
    "license": "AGPL-3",
    "development_status": "Alpha",
    "depends": [
        "account",
        "purchase",
        "shipment_advice",
    ],
    "data": ["views/account_move_views.xml"],
    "website": "https://github.com/OCA/stock-logistics-transport",
    "installable": True,
}
