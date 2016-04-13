# -*- coding: utf-8 -*-
# © initOS GmbH 2016
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Stock Picking Shipment Email",
    "version": "8.0.1.0.0",
    "depends": ["delivery",
                "stock",
                ],
    'author': 'initOS GmbH, Odoo Community Association (OCA)',
    "category": "",
    "summary": "",
    'license': 'AGPL-3',
    "description": """
Stock Picking Email
=======================================
* Send an email for the customer to notify him that his shipment is shipped
* Simple Email template that can be modified according to the customer needs
    """,
    'data': [
             'views/email.xml',
             'views/stock.xml',
             ],
    'images': [],
    'demo': [
    ],
    'test': [
    ],
    'installable': True,
    'auto_install': False,
}
