# -*- coding: utf-8 -*-
# Copyright 2014 Camptocamp SA - Leonardo Pistone
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Transport Information",
    "summary": "Transport Information",
    "version": "9.0.0.1.0",
    "author": "Camptocamp,Odoo Community Association (OCA)",
    "category": "Purchase Management",
    "license": "AGPL-3",
    "depends": ["purchase"],
    "data": [
        "security/ir.model.access.csv",
        "views/transport_mode_view.xml",
        "views/transport_vehicle_view.xml"
    ],
    'installable': True
}
