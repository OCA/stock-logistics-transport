{
    "name": "TMS Route Optimizer Distance Cache",
    "version": "18.0.1.0.0",
    "development_status": "Alpha",
    "category": "Inventory/Transport",
    "summary": "Distance matrix cache for TMS route optimization",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/stock-logistics-transport",
    "license": "AGPL-3",
    "depends": [
        "tms_route_optimizer",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_config_parameter.xml",
        "data/ir_cron.xml",
    ],
    "installable": True,
    "application": False,
}
