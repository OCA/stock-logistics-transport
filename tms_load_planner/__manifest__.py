# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "TMS Load Planner",
    "summary": "Vehicle layout, trip capacity checks, and a 3D load planner",
    "version": "19.0.1.19.0",
    "license": "AGPL-3",
    "category": "Transportation",
    "author": "Open Source Integrators, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/stock-logistics-transport",
    "depends": ["tms", "tms_sale"],
    "data": [
        "security/ir.model.access.csv",
        "data/cascadia_space_data.xml",
        "views/fleet_vehicle_model_views.xml",
        "views/fleet_vehicle_views.xml",
        "views/tms_cargo_views.xml",
        "views/tms_order_views.xml",
        "views/load_planner_views.xml",
    ],
    "demo": [
        "demo/vehicle_space_demo.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "tms_load_planner/static/src/lib/three.module.js",
            "tms_load_planner/static/src/load_planner/load_planner.scss",
            "tms_load_planner/static/src/load_planner/load_planner.xml",
            "tms_load_planner/static/src/load_planner/load_planner.esm.js",
        ],
    },
}
