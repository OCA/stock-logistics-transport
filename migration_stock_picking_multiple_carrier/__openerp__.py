# -*- coding: utf-8 -*-
# © 2016 initOS GmbH
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{'name': 'Migration Multiple Carrier',
 'version': '8.0.1.0.0',
 'category': '',
 'description': """
Migration - Multiple Carrier
=======================================

* Install this module to trigger the old carrier id and carrier references.
""",
 'depends': ['stock_picking_multiple_carrier',
             ],
 'author': "initOS GmbH, Odoo Community Association (OCA)",
 'website': "http://www.initos.com",
 'license': 'AGPL-3',
 'data': ['trigger.xml',
          ],
 'installable': True,
 'application': False,
 }
