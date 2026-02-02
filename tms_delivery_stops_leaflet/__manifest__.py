# Copyright (C) 2025 KMEE (https://kmee.com.br)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "TMS Delivery Stops - Leaflet Map",
    "summary": "Visualize delivery stops on interactive Leaflet maps.",
    "version": "18.0.2.0.0",
    "author": "KMEE, Odoo Community Association (OCA)",
    "maintainers": ["miloefb"],
    "development_status": "Beta",
    "website": "https://github.com/OCA/stock-logistics-transport",
    "license": "AGPL-3",
    "category": "Inventory/Transport",
    "depends": [
        "tms_delivery_stops",
        "web_view_leaflet_map",
        "web_leaflet_routing",
    ],
    "data": [
        "views/tms_order_stop_views.xml",
        "views/tms_order_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            # TMS Stops Map View - extends leaflet_map via js_class
            "tms_delivery_stops_leaflet/static/src/tms_stops_map/tms_stops_map_model.esm.js",
            "tms_delivery_stops_leaflet/static/src/tms_stops_map/tms_stops_map_renderer.esm.js",
            "tms_delivery_stops_leaflet/static/src/tms_stops_map/tms_stops_map_renderer.xml",
            "tms_delivery_stops_leaflet/static/src/tms_stops_map/tms_stops_map_view.esm.js",
            # TMS-specific styles (popup, legend, etc.)
            "tms_delivery_stops_leaflet/static/src/tms_stops_map/tms_stops_map.css",
        ],
    },
    "installable": True,
}
