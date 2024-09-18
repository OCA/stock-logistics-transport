# Copyright (C) 2024 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import _, api, fields, models


class TMSInsurance(models.Model):
    _name = "tms.insurance"

    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        help="Company related to this insurance",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
            ("expired", "Expired"),
            ("cancelled", "Cancelled"),
        ]
    )

    name = fields.Char(
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("Draft"),
        compute="_compute_name",
        store=True,
    )
    policy_number = fields.Char(required=True)
    insurer_id = fields.Many2one("res.partner", required=True)
    start_date = fields.Date()
    end_date = fields.Date(required=True)
    premium_amount = fields.Float()
    coverage_details = fields.Text()

    vehicle_ids = fields.Many2many("fleet.vehicle")

    _sql_constraints = [
        (
            "unique_policy_number_per_insurer",
            "UNIQUE(policy_number, insurer_id)",
            "The policy number must be unique for each insurer!",
        )
    ]

    @api.depends("insurer_id", "policy_number")
    def _compute_name(self):
        for record in self:
            if record.insurer_id and record.policy_number:
                insurer_name = record.insurer_id.name if record.insurer_id else ""
                record.name = f"{insurer_name}/{record.policy_number}"
