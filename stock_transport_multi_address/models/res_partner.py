# -*- coding: utf-8 -*-
# © 2015 Camptocamp SA - Alexandre Fayolle
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, fields


class ResPartner(models.Model):
    """Add fields related to consignee

    A consignee is a special kind of partner
    that is in charge of receiving goods.
    """

    _inherit = 'res.partner'

    is_consignee = fields.Boolean('Consignee')
