# Copyright (C) 2025 KMEE (https://kmee.com.br)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "TMS Route Optimizer - OSRM Distance Provider",
    "summary": "Use OSRM for real road distances instead of Haversine line-of-sight.",
    "version": "18.0.1.0.0",
    "author": "KMEE, Odoo Community Association (OCA)",
    "maintainers": ["miloefb"],
    "development_status": "Beta",
    "website": "https://github.com/OCA/stock-logistics-transport",
    "license": "AGPL-3",
    "category": "Inventory/Transport",
    "depends": [
        "tms_route_optimizer",
        "web_leaflet_lib",
    ],
    "external_dependencies": {
        "python": ["requests"],
    },
    "data": [
        "data/ir_config_parameter.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
}
