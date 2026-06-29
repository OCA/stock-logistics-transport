# Copyright (C) 2018 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "TMS - Purchase",
    "summary": "Manage purchase requests to drivers and other suppliers",
    "version": "19.0.1.0.0",
    "license": "AGPL-3",
    "category": "TMS",
    "author": "Open Source Integrators, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/stock-logistics-transport",
    "depends": ["tms", "tms_product", "purchase_stock"],
    "data": [
        "views/tms_order.xml",
        "views/purchase_order_views.xml",
        "views/fleet_vehicle_views.xml",
    ],
    "demo": [
        "demo/tms_purchase_fleet_vehicle_model_brand.xml",
        "demo/tms_purchase_fleet_vehicle_model.xml",
        "demo/tms_purchase_product_template.xml",
    ],
    "development_status": "Alpha",
    "maintainers": ["max3903", "santiagordz", "EdgarRetes"],
}
