# -*- coding: utf-8 -*-
# © 2015 Camptocamp SA - Alexandre Fayolle
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Stock - Transport Addresses',
    'summary': 'Manage origin / destination / consignee addresses on pickings',
    'version': '9.0.1.0.0',
    'author': "Camptocamp,"
              "Odoo Community Association (OCA)",
    'category': 'Warehouse',
    'complexity': 'expert',
    'website': "http://www.camptocamp.com",
    'depends': ['stock'],
    'demo': [],
    'data': [
        'views/stock_picking_view.xml',
        'views/res_partner_view.xml',
        'views/procurement_order_view.xml'
    ],
    'license': 'AGPL-3',
    'auto_install': False,
    'installable': True,
}
