# -*- coding: utf-8 -*-
# Copyright 2014 Camptocamp SA - Leonardo Pistone
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, fields


class TransportVehicle(models.Model):
    _name = "transport.vehicle"

    name = fields.Char('Name', required=True, translate=True)
