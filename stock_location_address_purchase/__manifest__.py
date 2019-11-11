# Copyright 2018 Creu Blanca
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

{
    'name': 'Purchase Location address',
    'summary': 'Uses the location address on purchases',
    'version': '12.0.1.0.0',
    'license': 'LGPL-3',
    'website': 'https://github.com/purchase-workflow',
    'author': 'Creu Blanca, '
              'Odoo Community Association (OCA)',
    'category': 'Purchases',
    'depends': [
        'purchase',
        'stock_location_address',
    ],
    'installable': True,
}
