# Copyright (C) 2018 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import ast

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    group_tms_route_analytic_plan = fields.Boolean(
        implied_group="tms_account.group_tms_route_analytic_plan",
        compute="_compute_tms_analytic_groups",
    )
    group_tms_order_analytic_plan = fields.Boolean(
        implied_group="tms_account.group_tms_order_analytic_plan",
        compute="_compute_tms_analytic_groups",
    )

    tms_analytic_plan = fields.Many2many(
        "account.analytic.plan",
        groups="analytic.group_analytic_accounting",
    )

    tms_analytic_plan_domain = fields.Char(
        default="[]",
        store=True,
        compute="_compute_tms_analytic_plan_domain",
        readonly=False,
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if not self.env.user.has_group("account.group_account_user"):
            res.pop("tms_analytic_plan", None)
        return res

    @api.depends("tms_analytic_plan", "group_tms_route", "group_analytic_accounting")
    def _compute_tms_analytic_plan_domain(self):
        domain = [("tms_flag", "=", True)]
        if (
            self.env.user.has_group("analytic.group_analytic_accounting")
            and not self.group_tms_route
        ):
            domain.append(
                (
                    "id",
                    "!=",
                    self.env.ref("tms_account.tms_route_analytic_plan").id,
                )
            )
        self.tms_analytic_plan_domain = domain

    @api.model
    def get_values(self):
        res = super().get_values()
        if self.env.user.has_group("analytic.group_analytic_accounting"):
            parameter = self.env["ir.config_parameter"].sudo()
            tms_analytic_plan_ids = parameter.get_param(
                "tms_account.tms_analytic_plan_ids", default="[]"
            )
            tms_analytic_plan_ids = ast.literal_eval(tms_analytic_plan_ids)
            res.update(
                tms_analytic_plan=[(6, 0, tms_analytic_plan_ids)]
                if tms_analytic_plan_ids
                else False,
            )
        return res

    def write(self, vals):
        if "tms_analytic_plan" in vals and not self.env.user.has_group(
            "analytic.group_analytic_accounting"
        ):
            vals.pop("tms_analytic_plan")
        return super().write(vals)

    def set_values(self):
        res = super().set_values()
        if self.env.user.has_group("analytic.group_analytic_accounting"):
            parameter = self.env["ir.config_parameter"].sudo()
            parameter.set_param(
                "tms_account.tms_analytic_plan_ids", self.tms_analytic_plan.ids
            )
        return res

    @api.depends("tms_analytic_plan")
    def _compute_tms_analytic_groups(self):
        route_plan_ref = self.env.ref("tms_account.tms_route_analytic_plan")
        order_plan_ref = self.env.ref("tms_account.tms_order_analytic_plan")
        parameter = self.env["ir.config_parameter"].sudo()
        stored_ids = ast.literal_eval(
            parameter.get_param("tms_account.tms_analytic_plan_ids", default="[]")
        )
        for record in self:
            record.group_tms_route_analytic_plan = False
            record.group_tms_order_analytic_plan = False

            if not self.env.user.has_group("analytic.group_analytic_accounting"):
                # Preserve groups from stored config so a non-analytic user
                # saving Settings does not revoke groups set by an admin.
                plan_ids = stored_ids
            else:
                plan_ids = record.sudo().tms_analytic_plan.ids

            if route_plan_ref.id in plan_ids:
                record.group_tms_route_analytic_plan = True
            if order_plan_ref.id in plan_ids:
                record.group_tms_order_analytic_plan = True
