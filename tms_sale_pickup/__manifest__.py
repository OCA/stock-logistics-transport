# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "TMS - Sale Pickup",
    "version": "19.0.1.0.0",
    "summary": "Record trip pickups and invoice the difference",
    "category": "TMS",
    "author": "Gray Matter Logic, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/stock-logistics-transport",
    "license": "AGPL-3",
    "development_status": "Alpha",
    "maintainers": ["max3903"],
    "depends": ["tms_account"],
    "data": [
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        "views/product_template_views.xml",
        "views/sale_order_views.xml",
        "views/tms_order_views.xml",
    ],
    "installable": True,
}
