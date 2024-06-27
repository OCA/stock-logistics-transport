# Copyright (C) 2018 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "TMS - Expense",
    "summary": "Manage expenses of a trip: hotel, tolls, fuel",
    "version": "17.0.1.0.0",
    "license": "AGPL-3",
    "category": "TMS",
    "author": "Open Source Integrators, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/stock-logistics-transport",
    "depends": ["tms", "hr_expense"],
    "data": [
        "data/hr_expense_data.xml",
        "data/hr_employee_driver.xml",
        "views/hr_expense_views.xml",
        "views/tms_order.xml",
    ],
    "demo": [],
    "development_status": "Alpha",
    "maintainers": ["max3903", "santiagordz", "EdgarRetes"],
}
