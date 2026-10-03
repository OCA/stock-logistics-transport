# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "TMS - Geotab",
    "summary": "Pull Geotab and AT&T Fleet Management feeds into TMS",
    "version": "19.0.1.0.0",
    "license": "AGPL-3",
    "category": "TMS",
    "author": "Gray Matter Logic, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/stock-logistics-transport",
    "depends": ["tms_telematics"],
    "data": [
        "views/tms_telematics_account.xml",
    ],
    "demo": [
        "demo/tms_telematics_account.xml",
        "demo/tms_telematics_device.xml",
    ],
    "development_status": "Alpha",
    "maintainers": ["max3903"],
}
