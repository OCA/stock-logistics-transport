# Copyright (C) 2024 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import date

from markupsafe import Markup

from odoo import _, api, fields, models


class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle"

    asset_id = fields.Many2one("account.asset", string="Asset")
    asset_profile_id = fields.Many2one(related="model_id.category_id.asset_profile_id")
    actual_value = fields.Monetary(related="asset_id.value_residual")

    @api.model
    def create(self, vals_list):
        vehicle = super().create(vals_list)

        asset_id = self.env["account.asset"].search([("vehicle_id", "=", vehicle.id)])
        from_asset = self.env.context.get("create_vehicle_from_asset")

        if asset_id or from_asset:
            return vehicle

        else:
            profile = self.env["account.asset.profile"].search(
                [("id", "=", vehicle.model_id.category_id.asset_profile_id.id)]
            )
            if profile:
                asset_vals_list = {
                    "name": f"VEHICLE - {vehicle.display_name}",
                    "purchase_value": 0.0,
                    "date_start": date.today(),
                    "profile_id": profile.id,
                    "vehicle_id": vehicle.id,
                    "model_id": vehicle.model_id.id,
                }
                AccountAsset = self.env["account.asset"]
                asset = AccountAsset.with_context(create_from_vehicle=True).create(
                    asset_vals_list
                )
                asset.write({})

                vehicle.asset_id = asset.id

                # Post a message in the chatter of the vehicle
                message = _(
                    "An asset has been created for this vehicle: %s",
                    Markup(
                        f"""<a href=# data-oe-model=account.asset"""
                        f"""data-oe-id={asset.id}"""
                        f""">{asset.display_name}</a>"""
                    ),
                )
                vehicle.message_post(body=message)

        return vehicle

    def action_view_asset(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.asset",
            "view_mode": "form",
            "res_id": self.asset_id.id,
            "target": "current",
            "name": _("Asset for vehicle: %s") % self.name,
        }
