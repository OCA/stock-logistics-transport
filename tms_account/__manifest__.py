# Copyright (C) 2024 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "TMS - Accounting",
    "summary": "Track invoices linked to TMS orders",
    "version": "17.0.1.0.0",
    "category": "Field Service",
    "author": "Open Source Integrators, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/stock-logistics-transport",
    "depends": ["tms", "tms_sale", "tms_expense", "tms_purchase", "account_usability"],
    "data": [
        "security/res_groups.xml",
        "data/analytic_plan.xml",
        "views/res_config_settings.xml",
        "views/account_move.xml",
        "views/account_analytic_plan.xml",
        "views/tms_order.xml",
        "views/tms_route.xml",
    ],
    "license": "AGPL-3",
    "development_status": "Alpha",
    "maintainers": ["max3903", "santiagordz", "EdgarRetes"],
}
