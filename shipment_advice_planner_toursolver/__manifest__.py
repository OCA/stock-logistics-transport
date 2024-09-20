# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Shipment Advice Planner Toursolver",
    "summary": """Shipment advices planning by geo-optimization (TourSolver)""",
    "version": "16.0.2.0.0",
    "license": "AGPL-3",
    "author": "ACSONE SA/NV,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/stock-logistics-transport",
    "depends": ["shipment_advice_planner", "base_time_window"],
    "data": [
        # data
        "data/toursolver_backend.xml",
        "data/ir_ui_menu.xml",
        "data/ir_sequence.xml",
        "data/ir_cron.xml",
        # security
        "security/toursolver_backend.xml",
        "security/toursolver_resource.xml",
        "security/toursolver_task.xml",
        "security/toursolver_delivery_window.xml",
        "security/toursolver_backend_option_definition.xml",
        # views
        "views/shipment_advice.xml",
        "views/toursolver_backend.xml",
        "views/res_config_settings.xml",
        "views/toursolver_resource.xml",
        "views/stock_picking.xml",
        "views/toursolver_delivery_window.xml",
        "views/toursolver_task.xml",
        "views/res_partner.xml",
        # wizards
        "wizards/shipment_advice_planner.xml",
    ],
    "demo": [
        "demo/toursolver_backend.xml",
        "demo/toursolver_resource.xml",
        "demo/res_compnay.xml",
    ],
}
