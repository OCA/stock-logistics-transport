# Copyright 2021 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

{
    "name": "Shipment Advice",
    "summary": "Manage your (un)loading process through shipment advices.",
    "version": "13.0.1.0.1",
    "author": "Camptocamp, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/stock-logistics-transport",
    "category": "Warehouse Management",
    "depends": [
        "stock",
        "delivery",
        # OCA/stock-logistics-transport
        "stock_dock",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence.xml",
        "views/res_config_settings.xml",
        "views/shipment_advice.xml",
        "views/stock_picking.xml",
        "views/stock_package_level.xml",
        "views/stock_move.xml",
        "views/stock_move_line.xml",
        "wizards/plan_shipment.xml",
        "wizards/unplan_shipment.xml",
        "wizards/load_shipment.xml",
        "wizards/unload_shipment.xml",
        "report/reports.xml",
        "report/report_shipment_advice.xml",
    ],
    "demo": ["demo/stock_dock.xml"],
    "license": "AGPL-3",
    "installable": True,
    "application": False,
}
