# Copyright (C) 2026 VSL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "TMS Document",
    "summary": "Generic expiry-tracked document framework for TMS",
    "version": "19.0.1.0.2",
    "license": "AGPL-3",
    "category": "TMS",
    "author": "VSL, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/stock-logistics-transport",
    "maintainers": ["volkantasci"],
    "development_status": "Alpha",
    "installable": True,
    "application": False,
    "depends": ["tms"],
    "data": [
        "security/res_groups.xml",
        "security/ir.model.access.csv",
        "data/ir_config_parameter.xml",
        "views/tms_document_views.xml",
        "views/tms_driver_views.xml",
        "views/fleet_vehicle_views.xml",
        "views/menu.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "tms_document/static/src/form/form_controller.esm.js",
            "tms_document/static/src/form/form_buttons.xml",
        ],
    },
}
