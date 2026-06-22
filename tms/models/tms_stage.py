# Copyright (C) 2024 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class TMSStage(models.Model):
    _name = "tms.stage"
    _description = "Transport Management System Stage"
    _order = "sequence, name, id"

    def _default_tms_team_ids(self):
        default_tms_team_id = self.env.context.get("default_tms_team_id")
        return [default_tms_team_id] if default_tms_team_id else None

    active = fields.Boolean(default=True)
    name = fields.Char(required=True)
    sequence = fields.Integer(default=1, help="Used to order stages. Lower is first.")
    legend_priority = fields.Text(
        "Priority Management Explanation",
        translate=True,
        help="Explanation text to help users using"
        " the star and priority mechanism on"
        " stages or orders that are in this"
        " stage.",
    )
    fold = fields.Boolean(
        "Folded in Kanban",
        help="This stage is folded in the kanban view when "
        "there are no record in that stage to display.",
    )
    is_completed = fields.Boolean(
        help="Defines how this stage is evaluated as completed stage",
    )
    is_default = fields.Boolean(readonly=True, default=False)
    custom_color = fields.Char(
        "Color Code", default="#FFFFFF", help="Use Hex Code only Ex:-#FFFFFF"
    )
    description = fields.Text(translate=True)
    stage_type = fields.Selection(
        [
            ("driver", "Driver"),
            ("order", "Trip"),
        ],
        string="Type",
        required=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.user.company_id.id,
    )

    tms_team_ids = fields.Many2many(
        "tms.team",
        "tms_order_team_stage_rel",
        "stage_id",
        "tms_team_id",
        string="Teams",
        default=lambda self: self._default_tms_team_ids(),
    )

    def get_color_information(self):
        stages = self.env["tms.stage"]
        stage_ids = stages.browse(stages._search([]))
        color_information_dict = []
        for stage in stage_ids:
            color_information_dict.append(
                {
                    "color": stage.custom_color,
                    "field": "stage_id",
                    "opt": "==",
                    "value": stage.name,
                }
            )
        return color_information_dict

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            stage_type = vals.get("stage_type")
            sequence = vals.get("sequence")
            if stage_type is None or sequence is None:
                continue
            if self.search_count(
                [("stage_type", "=", stage_type), ("sequence", "=", sequence)]
            ):
                raise ValidationError(
                    self.env._(
                        "Cannot create TMS Stage because "
                        "it has the same Type and Sequence "
                        "of an existing TMS Stage."
                    )
                )
        return super().create(vals_list)

    @api.constrains("custom_color")
    def _check_custom_color_hex_code(self):
        if (
            self.custom_color
            and not self.custom_color.startswith("#")
            or len(self.custom_color) != 7
        ):
            raise ValidationError(
                self.env._("Color code should be Hex Code. Ex:-#FFFFFF")
            )

    @api.ondelete(at_uninstall=False)
    def _unlink_except_default(self):
        if any(stage.is_default for stage in self):
            raise UserError(self.env._("You cannot delete default stages."))
