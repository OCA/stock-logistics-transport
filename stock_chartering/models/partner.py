from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_boarding = fields.Boolean(
        help="Place used as landing or boarding place for container vehicles"
    )
