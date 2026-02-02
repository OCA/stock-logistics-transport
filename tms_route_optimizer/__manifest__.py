{
    "name": "TMS Route Optimizer",
    "version": "18.0.1.0.0",
    "development_status": "Alpha",
    "category": "Inventory/Transport",
    "summary": "Route optimization using Google OR-Tools",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/stock-logistics-transport",
    "license": "AGPL-3",
    "depends": [
        "tms",
        "tms_delivery_stops",
        "tms_vehicle_capacity",
        "base_geolocalize",
        "mail",
    ],
    "external_dependencies": {
        "python": ["ortools"],
    },
    "data": [
        "security/ir.model.access.csv",
        "views/tms_route_optimizer.xml",
        "views/tms_route_optimizer_config.xml",
        "views/tms_route_suggestion.xml",
        "views/tms_route_optimizer_menu.xml",
        "data/ir_config_parameter.xml",
        "data/ir_cron.xml",
    ],
    "demo": [
        "data/demo_data.xml",
    ],
    "installable": True,
    "application": False,
}
