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
    _description = "Model for TMS drivers"

    partner_id = fields.Many2one("res.partner", required=True, ondelete="cascade")

    # ------------------------------
    #            Driver
    # ------------------------------

    # Driver - Flags
    is_external = fields.Boolean(string="External Driver", tracking=True)
    is_training = fields.Boolean(string="In Training", tracking=True)
    is_active = fields.Boolean(default=True, tracking=True)

    # Driver - Relations
    vehicles_ids = fields.One2many("fleet.vehicle", "driver_id")
    trips_ids = fields.One2many("tms.order", "driver_id")

    tms_team_id = fields.Many2one("tms.team", tracking=True)
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
        tracking=True,
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
    driver_license_number = fields.Char(tracking=True)
    driver_license_type = fields.Selection(
        string="License type", selection=DRIVER_LICENSE_TYPES, tracking=True
    )
    driver_license_expiration_date = fields.Date(tracking=True)
    driver_license_file = fields.Binary()

    # Terrestrial - Experience
    distance_traveled = fields.Integer(tracking=True)
    distance_traveled_uom = fields.Selection(
        selection=[("km", "km"), ("mi", "mi")], default="km", tracking=True
    )
    driving_experience_years = fields.Integer(tracking=True)

    @api.model
    def _read_group_stage_ids(self, stages, domain, order=None):
        order = order or "sequence, id"
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

    def _creation_message(self):
        self.ensure_one()
        return self.env._("Driver created")

    def _track_subtype(self, init_values):
        self.ensure_one()
        if "stage_id" in init_values:
            return self.env.ref("tms.mt_driver_stage")
        return super()._track_subtype(init_values)

    # Inherited actions from res_partner

    def create_company(self):
        return self.partner_id.create_company()

    def action_open_employees(self):
        return self.partner_id.action_open_employees()

    def open_commercial_entity(self):
        return self.partner_id.open_commercial_entity()

    def phone_action_blacklist_remove(self):
        return self.partner_id.phone_action_blacklist_remove()

    def mail_action_blacklist_remove(self):
        return self.partner_id.mail_action_blacklist_remove()

    def geo_localize(self):
        return self.partner_id.geo_localize()

    def schedule_meeting(self):
        return self.partner_id.schedule_meeting()

    def action_view_partner_invoices(self):
        return self.partner_id.action_view_partner_invoices()

    def action_view_stock_serial(self):
        return self.partner_id.action_view_stock_serial()
