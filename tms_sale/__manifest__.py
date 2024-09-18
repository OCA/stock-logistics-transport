# Copyright (C) 2018 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "TMS - Sales",
    "version": "17.0.1.0.0",
    "summary": "Sell transportation management system.",
    "category": "TMS",
    "author": "Open Source Integrators, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/stock-logistics-transport",
    "depends": ["tms", "tms_product", "sale_management", "web"],
    "data": [
        "security/ir.model.access.csv",
        "wizard/sale_order_line_trip_views.xml",
        "wizard/seat_ticket_line_views.xml",
        "views/sale_order_views.xml",
        "views/tms_order_views.xml",
        "views/product_template_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "tms_sale/static/src/js/line_trip_wizard_controller.js",
            "tms_sale/static/src/js/line_ticket_wizard_controller.js",
            "tms_sale/static/src/js/sale_order_line_product_field.js",
        ],
    },
    "license": "AGPL-3",
    "development_status": "Alpha",
    "maintainers": ["max3903", "santiagordz", "EdgarRetes"],
    "installable": True,
}
