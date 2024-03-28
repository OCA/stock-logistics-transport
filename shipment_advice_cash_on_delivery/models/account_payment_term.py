# Copyright 2018 Jacques-Etienne Baudoux (BCIM) <je@bcim.be>

from odoo import fields, models


class AccountPaymentTerm(models.Model):
    _inherit = "account.payment.term"

    cash_on_delivery = fields.Boolean("Cash on Delivery")
