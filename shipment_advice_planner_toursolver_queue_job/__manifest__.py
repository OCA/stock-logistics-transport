# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Shipment Advice Planner Toursolver Queue Job",
    "summary": """Run TourSolver queries in queue jobs""",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "ACSONE SA/NV,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/stock-logistics-transport",
    "depends": ["shipment_advice_planner_toursolver", "queue_job", "web_notify"],
    "data": ["data/queue_job_channel.xml", "data/queue_job_function.xml"],
    "demo": [],
}
