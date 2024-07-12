# Copyright 2024 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{
    "name": "Shipment Advice Bill Auto Complete MRP",
    "summary": "Glue module between Shipment Advice Bill Auto Complete and MRP",
    "version": "14.0.1.1.0",
    "category": "Invoicing Management",
    "author": "Camptocamp, Odoo Community Association (OCA)",
    "maintainers": ["TDu"],
    "license": "AGPL-3",
    "development_status": "Alpha",
    "depends": [
        "shipment_advice_bill_auto_complete",
        "purchase_mrp",
    ],
    "website": "https://github.com/OCA/stock-logistics-transport",
    "auto_install": True,
    "installable": True,
}
