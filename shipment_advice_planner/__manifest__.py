# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Shipment Advice Planner",
    "summary": """This module is used to plan ready transfers in shipment advices.""",
    "version": "18.0.1.1.0",
    "license": "AGPL-3",
    "author": "ACSONE SA/NV,BCIM,Odoo Community Association (OCA)",
    "maintainers": ["jbaudoux"],
    "website": "https://github.com/OCA/stock-logistics-transport",
    "depends": ["shipment_advice"],
    "data": [
        "security/shipment_advice_planner.xml",
        "wizards/shipment_advice_planner.xml",
    ],
    "demo": [],
}
