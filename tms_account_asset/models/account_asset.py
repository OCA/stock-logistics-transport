# Copyright (C) 2024 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountAsset(models.Model):
    _inherit = "account.asset"

    vehicle_id = fields.Many2one("fleet.vehicle", store=True, ondelete="cascade")
    asset_ids = fields.One2many("fleet.vehicle", "asset_id")

    is_vehicle = fields.Boolean(related="profile_id.is_vehicle")
    model_id = fields.Many2one(
        "fleet.vehicle.model",
        help="If not a vehicle assigned to this asset, "
        "change the model to create a vehicle of the selected model",
    )

    @api.constrains("name", "vehicle_id")
    def _check_name_uniqueness(self):
        for record in self:
            if record.vehicle_id:
                existing_asset = self.search(
                    [
                        ("name", "=", record.name),
                        ("id", "!=", record.id),
                        ("vehicle_id", "!=", False),
                    ]
                )
                if existing_asset:
                    raise ValidationError(
                        _(
                            "An asset with this name already exists "
                            "for the specified vehicle."
                        )
                    )

    @api.model
    def create(self, vals_list):
        asset = super().create(vals_list)

        vehicle_id = self.env["fleet.vehicle"].search([("asset_id", "=", asset.id)])
        from_vehicle = self.env.context.get("create_from_vehicle")

        if vehicle_id or from_vehicle:
            return asset

        elif not asset.profile_id.is_vehicle:
            return asset

        else:
            asset._create_vehicle()
            return asset

    def _create_vehicle(self):
        for asset in self:
            vehicle_vals_list = {"model_id": asset.model_id.id, "asset_id": asset.id}
            vehicle = (
                self.env["fleet.vehicle"]
                .with_context(create_vehicle_from_asset=True)
                .create([vehicle_vals_list])
            )
            asset.vehicle_id = vehicle.id

            # Post a message in the chatter of the vehicle
            message = _(
                "A vehicle has been created for this asset: %s",
                Markup(
                    f"""<a href=# data-oe-model=fleet.vehicle data-oe-id={vehicle.id}"""
                    f""">{vehicle.display_name}</a>"""
                ),
            )
            asset.message_post(body=message)

    def action_view_vehicle(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "fleet.vehicle",
            "view_mode": "form",
            "res_id": self.vehicle_id.id,
            "target": "current",
            "name": _("Vehicle for asset: %s") % self.name,
        }
