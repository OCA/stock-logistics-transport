# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "TMS - Portal",
    "version": "19.0.1.0.0",
    "summary": "Let external drivers record pickups on their trips",
    "category": "TMS",
    "author": "Gray Matter Logic, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/stock-logistics-transport",
    "license": "AGPL-3",
    "development_status": "Alpha",
    "maintainers": ["max3903"],
    "depends": ["tms_sale_pickup", "portal"],
    "data": [
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        "views/portal_templates.xml",
    ],
    "installable": True,
}
