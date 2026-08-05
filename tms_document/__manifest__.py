# Copyright (C) 2026 VSL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "TMS Document",
    "summary": "Generic expiry-tracked document framework for TMS",
    "version": "19.0.1.0.0",
    "license": "AGPL-3",
    "category": "TMS",
    "author": "VSL, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/stock-logistics-transport",
    "maintainers": ["volkantasci"],
    "development_status": "Beta",
    "installable": True,
    "application": False,
    "depends": ["tms"],
    "data": [
        "security/res_groups.xml",
        "security/ir.model.access.csv",
    ],
}
