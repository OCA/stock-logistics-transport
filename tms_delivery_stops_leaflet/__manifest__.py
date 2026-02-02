# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "TMS Delivery Stops - Leaflet Map Visualization",
    "summary": "Visualize TMS delivery stops on Leaflet maps with selection support.",
    "version": "18.0.1.0.0",
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
    ],
    "demo": [
        "demo/demo_unallocated_stops.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "tms_delivery_stops_leaflet/static/src/tms_stops_map/selectable_pin_list.esm.js",
            "tms_delivery_stops_leaflet/static/src/tms_stops_map/selectable_pin_list.xml",
            "tms_delivery_stops_leaflet/static/src/tms_stops_map/selectable_pin_list.css",
            "tms_delivery_stops_leaflet/static/src/tms_stops_map/tms_stops_map_model.esm.js",
            "tms_delivery_stops_leaflet/static/src/tms_stops_map/tms_stops_map_renderer.esm.js",
            "tms_delivery_stops_leaflet/static/src/tms_stops_map/tms_stops_map_renderer.xml",
            "tms_delivery_stops_leaflet/static/src/tms_stops_map/tms_stops_map_view.esm.js",
        ],
    },
    "installable": True,
}
