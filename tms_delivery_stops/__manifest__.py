{
    "name": "TMS Delivery Stops",
    "version": "18.0.1.0.0",
    "development_status": "Alpha",
    "category": "Inventory/Transport",
    "summary": "Support for multiple delivery stops per TMS order",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/stock-logistics-transport",
    "license": "AGPL-3",
    "depends": [
        "tms",
        "base_geolocalize",
        "uom",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizard/create_order_from_stops_wizard.xml",
        "views/res_config_settings.xml",
        "views/tms_stage.xml",
        "views/tms_order_stop.xml",
        "views/tms_order.xml",
        "views/tms_team.xml",
    ],
    "demo": [
        "demo/demo_data.xml",
    ],
    "installable": True,
    "application": False,
}
