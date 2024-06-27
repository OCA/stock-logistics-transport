# Copyright (C) 2018 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "TMS - Account Assets",
    "summary": "Manage TMS assets",
    "version": "17.0.1.0.0",
    "license": "AGPL-3",
    "category": "TMS",
    "author": "Open Source Integrators, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/stock-logistics-transport",
    "depends": ["tms", "tms_product", "account_asset_management"],
    "data": [
        "views/account_asset_profile_views.xml",
        "views/account_asset_views.xml",
        "views/fleet_vehicle_model_category_views.xml",
        "views/fleet_vehicle_views.xml",
    ],
    "demo": [],
    "development_status": "Alpha",
    "maintainers": ["max3903", "santiagordz", "EdgarRetes"],
}
