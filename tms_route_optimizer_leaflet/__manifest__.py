# Copyright (C) 2025 KMEE (https://kmee.com.br)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "TMS Route Optimizer - Leaflet Map Visualization",
    "summary": "Visualize optimized TMS routes on Leaflet maps with polylines.",
    "version": "18.0.1.0.0",
    "author": "KMEE, Odoo Community Association (OCA)",
    "maintainers": ["miloefb"],
    "development_status": "Beta",
    "website": "https://github.com/OCA/stock-logistics-transport",
    "license": "AGPL-3",
    "category": "Inventory/Transport",
    "depends": [
        "tms_route_optimizer",
        "tms_delivery_stops",
        "web_view_leaflet_map",
        "web_leaflet_routing",
    ],
    "data": [
        "views/tms_order_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "tms_route_optimizer_leaflet/static/src/tms_map_renderer.esm.js",
            "tms_route_optimizer_leaflet/static/src/tms_map_renderer.xml",
            "tms_route_optimizer_leaflet/static/src/tms_map_renderer.css",
        ],
    },
    "installable": True,
}
