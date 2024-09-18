# Copyright (C) 2018 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

DRIVER_LICENSE_TYPES = [
    ("A", "A - Motorcycles"),
    ("B", "B - Automobiles"),
    ("C", "C - Truck"),
    ("D", "D - Bus"),
]
LOCATION_TYPES = [("terrestrial", "Terrestrial")]


class TmsDriver(models.Model):
    _name = "tms.driver"
    _inherit = ["mail.thread"]
    _inherits = {"res.partner": "partner_id"}

    partner_id = fields.Many2one("res.partner", required=True, ondelete="cascade")

    # ------------------------------
    #            Driver
    # ------------------------------

    # Driver - Flags
    is_external = fields.Boolean(string="External Driver")
    is_training = fields.Boolean(string="In Training")
    is_active = fields.Boolean(default=True)

    # Driver - Relations
    vehicles_ids = fields.One2many("fleet.vehicle", "driver_id")
    trips_ids = fields.One2many("tms.order", "driver_id")

    tms_team_id = fields.Many2one("tms.team")
    crew_ids = fields.Many2many(
        "tms.crew",
        "tms_crew_drivers_rel",
        string="Crews",
    )
    stage_id = fields.Many2one(
        "tms.stage",
        string="Stage",
        index=True,
        copy=False,
        default=lambda self: self._default_stage_id(),
        group_expand="_read_group_stage_ids",
    )

    # Driver - Type
    driver_type = fields.Selection(
        string="Type", selection=[("terrestrial", "Terrestrial")]
    )

    # ------------------------------
    #      Driver - Terrestrial
    # ------------------------------

    # TODO: ADD A LICENCE MODEL
    # Terrestrial - Licenses
    driver_license_number = fields.Char()
    driver_license_type = fields.Selection(
        string="License type", selection=DRIVER_LICENSE_TYPES
    )
    driver_license_expiration_date = fields.Date()
    driver_license_file = fields.Binary()

    # Terrestrial - Experience
    distance_traveled = fields.Integer()
    distance_traveled_uom = fields.Selection(
        selection=[("km", "km"), ("mi", "mi")], default="km"
    )
    driving_experience_years = fields.Integer()

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        return self.env["tms.stage"].search(
            [("stage_type", "=", "driver")], order=order
        )

    def _default_stage_id(self):
        stage = self.env["tms.stage"].search(
            [("stage_type", "=", "driver")],
            order="sequence asc",
            limit=1,
        )
        if stage:
            return stage.id

    # Inherited actions from res_partner

    def create_company(self):
        res = super().create_company()
        return res

    def action_open_employees(self):
        res = super().action_open_employees()
        return res

    def open_commercial_entity(self):
        res = super().open_commercial_entity()
        return res

    def phone_action_blacklist_remove(self):
        res = super().phone_action_blacklist_remove()
        return res

    def mail_action_blacklist_remove(self):
        res = super().mail_action_blacklist_remove()
        return res

    def geo_localize(self):
        res = super().geo_localize()
        return res
