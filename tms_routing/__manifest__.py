# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "TMS - Routing",
    "summary": "Compute a route distance and duration from a path provider",
    "version": "19.0.1.0.0",
    "license": "AGPL-3",
    "category": "TMS",
    "author": "Gray Matter Logic, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/stock-logistics-transport",
    "depends": ["tms", "queue_job"],
    "data": [
        "security/ir.model.access.csv",
        "data/queue_job_channel.xml",
        "views/tms_route.xml",
    ],
    "development_status": "Beta",
    "maintainers": ["max3903"],
    "installable": True,
}
