{
    "name": "TMS Vehicle Capacity",
    "version": "18.0.1.0.0",
    "development_status": "Alpha",
    "category": "Inventory/Transport",
    "summary": "Vehicle types with capacity and cost management for TMS",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/stock-logistics-transport",
    "license": "AGPL-3",
    "depends": [
        "tms",
        "fleet",
        "uom",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/fleet_vehicle_type.xml",
        "views/fleet_vehicle_model.xml",
        "views/fleet_vehicle.xml",
        "views/tms_team.xml",
        "data/fleet_vehicle_type_data.xml",
    ],
    "demo": [
        "data/demo_data.xml",
    ],
    "installable": True,
    "application": False,
}
