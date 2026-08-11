# Copyright (C) 2026 VSL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "TMS Document",
    "summary": "Generic expiry-tracked document framework for TMS",
    "version": "19.0.1.0.4",
    "license": "AGPL-3",
    "category": "TMS",
    "author": "Volkan Taşçı, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/stock-logistics-transport",
    "maintainers": ["volkantasci"],
    "development_status": "Alpha",
    "installable": True,
    "application": False,
    "depends": ["tms"],
    "data": [
        "security/res_groups.xml",
        "security/ir.model.access.csv",
        "security/ir_rules.xml",
        "data/ir_config_parameter.xml",
        "views/tms_document_views.xml",
        "views/tms_driver_views.xml",
        "views/fleet_vehicle_views.xml",
        "views/menu.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "tms_document/static/src/document_uploader/document_uploader.esm.js",
            "tms_document/static/src/document_uploader/document_uploader.xml",
        ],
    },
}
