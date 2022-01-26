# Copyright 2022 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
{
    "name": "Shipment Planning",
    "summary": "Plan (un)loading process through shipment plannings.",
    "version": "14.0.1.0.0",
    "development_status": "Alpha",
    "author": "Camptocamp, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/stock-logistics-transport",
    "category": "Warehouse Management",
    "depends": [
        "stock",
        "web_domain_field",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence.xml",
        "views/shipment_planning.xml",
    ],
    "license": "AGPL-3",
    "installable": True,
    "application": False,
}
