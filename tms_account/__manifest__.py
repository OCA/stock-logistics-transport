# Copyright (C) 2024 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "TMS - Accounting",
    "summary": "Track invoices linked to TMS orders",
    "version": "17.0.1.0.0",
    "category": "Field Service",
    "author": "Open Source Integrators, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/stock-logistics-transport",
    "depends": ["tms", "account", "tms_sale", "tms_purchase"],
    "data": [
        "views/account_move.xml",
        "views/tms_order.xml",
    ],
    "license": "AGPL-3",
    "development_status": "Alpha",
    "maintainers": ["max3903", "santiagordz", "EdgarRetes"],
}
