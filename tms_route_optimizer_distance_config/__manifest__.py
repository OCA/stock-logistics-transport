# Copyright (C) 2025 KMEE (https://kmee.com.br)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "TMS Route Optimizer - Distance Configuration",
    "summary": "UI for configuring distance providers (Haversine, OSRM, Google).",
    "version": "18.0.1.0.0",
    "author": "KMEE, Odoo Community Association (OCA)",
    "maintainers": ["miloefb"],
    "development_status": "Beta",
    "website": "https://github.com/OCA/stock-logistics-transport",
    "license": "AGPL-3",
    "category": "Inventory/Transport",
    "depends": [
        "tms_route_optimizer",
    ],
    "data": [
        "data/ir_config_parameter.xml",
        "views/res_config_settings.xml",
    ],
    "installable": True,
}
