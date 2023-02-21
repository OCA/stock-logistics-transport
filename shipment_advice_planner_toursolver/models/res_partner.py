# Copyright 2020 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import fields, models


class ResPartner(models.Model):

    _inherit = "res.partner"

    toursolver_delivery_window_ids = fields.One2many(
        comodel_name="toursolver.delivery.window",
        inverse_name="partner_id",
        string="Delivery windows",
        help="If specified, delivery is only possible into the specified "
        "time windows. (Leaves empty if no restriction)",
    )
    toursolver_delivery_duration = fields.Integer()

    def _get_delivery_windows(self, day_name):
        """
        Return the list of delivery windows by partner id for the given day.

        :param day: The day name (see time.weekday)
        :return: dict partner_id:[delivery_window, ]
        """
        self.ensure_one()
        week_day_id = self.env["time.weekday"]._get_id_by_name(day_name)
        return self.env["toursolver.delivery.window"].search(
            [
                ("partner_id", "=", self.id),
                ("time_window_weekday_ids", "in", week_day_id),
            ]
        )
