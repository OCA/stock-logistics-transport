# Copyright (C) 2018 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "TMS - Product",
    "summary": "Manage Vehicles as Products",
    "version": "17.0.1.0.0",
    "license": "AGPL-3",
    "category": "TMS",
    "author": "Open Source Integrators, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/stock-logistics-transport",
    "depends": ["tms", "stock", "product"],
    "data": [
        "security/ir.model.access.csv",
        "views/transportable_product_views.xml",
        "views/fleet_vehicle_views.xml",
        "views/product_template_views.xml",
        "views/stock_lot_views.xml",
        "views/stock_picking_views.xml",
    ],
    "development_status": "Alpha",
    "maintainers": ["max3903", "santiagordz", "EdgarRetes"],
}
