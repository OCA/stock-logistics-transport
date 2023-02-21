# Copyright 2020 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import fields, models


class ToursolverDeliveryWindow(models.Model):

    _name = "toursolver.delivery.window"
    _inherit = "time.window.mixin"
    _description = "TourSolver Delivery Window"
    _order = "partner_id, time_window_start"
    _time_window_overlap_check_field = "partner_id"

    partner_id = fields.Many2one(
        comodel_name="res.partner", required=True, index=True, ondelete="cascade"
    )
