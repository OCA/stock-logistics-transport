# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .tools import seconds_to_duration


class TourSolverBackend(models.Model):
    _name = "toursolver.backend"
    _description = "TourSolver Backend"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    resource_properties_definition = fields.PropertiesDefinition(
        string="Resource Properties"
    )
    url = fields.Char()
    api_key = fields.Char()
    delivery_window_disabled = fields.Boolean()
    partner_defaul_delivery_window_start = fields.Float(
        default=8.0,
        help="If no delivery winodow specified on the partner this will be used",
    )
    partner_default_delivery_window_end = fields.Float(
        default=17.0,
        help="If no delivery winodow specified on the partner this will be used",
    )
    delivery_duration = fields.Integer(
        string="Fixed time spent delivering a customer",
        help="Duration in seconds needed to deliver a customer",
        default=180,
    )
    duration = fields.Integer(
        string="Optimization process max duration",
        help="Duration in seconds allowed to the computation of the optimization",
    )
    loading_duration = fields.Integer(
        string="Fixed initial loading time", help="Loading time in minutes"
    )
    resource_default_work_penalty = fields.Float(
        string="Resource fixed cost working/hour",
        help="Default value for the cost of a resource working for an hour. "
        "Can be specified on resource level using `travelPenalty`option",
    )
    resource_default_travel_penalty = fields.Float(
        string="Resource fixed cost travelling/hour",
        help="Default value for the The cost for a resource of driving for one distance"
        " unit. Can be specified on resource level using `workPenalty`option",
    )
    definition_id = fields.Many2one(
        comodel_name="toursolver.backend.option.definition", readonly=True
    )
    backend_options = fields.Properties(
        string="Options",
        copy=True,
        definition="definition_id.backend_options_definition",
    )
    organization = fields.Char(
        help="Organization identifier as specified in the Toursolver interface. If set, "
        "it's used to define how see the results in the Toursolver interface and to "
        "determine the time zone of the optimization. If not provided, the server will "
        "guess the time zone from the first visit coordinates which will add extra time "
        "to the optimization process."
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            rec.definition_id = rec.definition_id.create({})
        return records

    def _get_partner_delivery_duration(self, partner):
        self.ensure_one()
        return (
            partner.toursolver_delivery_duration
            if partner.toursolver_delivery_duration
            else self.delivery_duration
        )

    def _get_work_start_time(self):
        """
        Return the start time of the delivery to geo-optimize.

        The start time is now + the geo optimization duration
        """
        self.ensure_one()
        tz_name = self.env.context.get("tz") or self.env.user.tz
        if not tz_name:
            raise UserError(
                _("Please configure your timezone in your user preferences")
            )
        m, s = divmod(self.duration, 60)
        now = fields.Datetime.context_timestamp(self, datetime.now())
        return now + timedelta(minutes=m, seconds=s)

    def _get_work_start_time_formatted(self):
        return self._get_work_start_time().strftime("%H:%M:00")

    def _get_loading_duration_formatted(self):
        h, m = divmod(self.loading_duration, 60)
        return f"{h:02d}:{m:02d}:00"

    def _get_backend_default_options(self):
        return {"maxOptimDuration": seconds_to_duration(self.duration)}

    def _get_backend_options(self):
        self.ensure_one()
        result = self._get_backend_default_options()
        result.update({p.get("string"): p.get("value") for p in self.backend_options})
        return result
