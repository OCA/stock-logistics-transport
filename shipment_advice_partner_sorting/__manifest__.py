# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
{
    "name": "Shipment Advice Partner Sorting",
    "summary": "Sequence planned transfers by delivery partner",
    "version": "16.0.1.0.0",
    "author": "ACSONE SA/NV,BCIM,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/stock-logistics-transport",
    "license": "AGPL-3",
    "depends": ["shipment_advice"],
    "data": [
        "security/ir.model.access.csv",
        "views/shipment_advice_planned_partner_order.xml",
        "views/shipment_advice.xml",
        "views/stock_picking.xml",
        "views/stock_move.xml",
    ],
    "installable": True,
    "maintainers": ["lmignon", "jbaudoux"],
}
