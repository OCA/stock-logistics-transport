# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "TMS - Telematics Expense",
    "summary": "Create a fuel expense from a telematics fill",
    "version": "19.0.1.0.0",
    "license": "AGPL-3",
    "category": "TMS",
    "author": "Gray Matter Logic, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/stock-logistics-transport",
    "depends": ["tms_telematics", "tms_expense"],
    "data": [
        "views/tms_telematics_reading.xml",
    ],
    "demo": [
        "demo/tms_telematics_reading.xml",
    ],
    "development_status": "Alpha",
    "maintainers": ["max3903"],
}
