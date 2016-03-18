# -*- coding: utf-8 -*-
# © 2016 initOS GmbH
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Multiple Carriers",
    "version": "8.0.1.0.0",
    "depends": ["delivery",
                "stock",
                ],
    "author": 'initOS GmbH, Odoo Community Association (OCA)',
    "website": "http://www.initos.com",
    "category": "",
    "summary": "",
    'license': 'AGPL-3',
    "description": """
Multiple carriers per picking.
=======================================
Each picking can have more than one Carrier
the user can select the carrier type
and assign a tracking number for it
    """,
    'data': ['security/ir.model.access.csv',
             'stock_picking_views.xml',
             ],
    'images': [],
    'demo': [
    ],
    'test': [
    ],
    'installable': True,
    'auto_install': False,
}
