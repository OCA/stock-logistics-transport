# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "TMS - Telematics",
    "summary": "Import GPS, odometer, and fuel events into trips",
    "version": "19.0.1.0.0",
    "license": "AGPL-3",
    "category": "TMS",
    "author": "Gray Matter Logic, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/stock-logistics-transport",
    "depends": ["tms", "queue_job"],
    "data": [
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        "data/queue_job_channel.xml",
        "data/ir_cron.xml",
        "views/tms_telematics_account.xml",
        "views/tms_telematics_device.xml",
        "views/tms_telematics_reading.xml",
        "views/menu.xml",
    ],
    "demo": [
        "demo/tms_telematics_account.xml",
        "demo/tms_telematics_device.xml",
        "demo/tms_telematics_reading.xml",
    ],
    "development_status": "Alpha",
    "maintainers": ["max3903"],
}
