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
    )

    tms_analytic_plan_domain = fields.Char(
        default="[]",
        store=True,
        compute="_compute_tms_analytic_plan_domain",
        readonly=False,
    )

    @api.depends("tms_analytic_plan", "group_tms_route", "group_analytic_accounting")
    def _compute_tms_analytic_plan_domain(self):
        if not self.group_tms_route:
            domain = [
                ("tms_flag", "=", True),
                ("id", "!=", self.env.ref("tms_account.tms_route_analytic_plan").id),
            ]
        else:
            domain = [("tms_flag", "=", True)]
        self.tms_analytic_plan_domain = domain

    @api.model
    def get_values(self):
        res = super().get_values()
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

    def set_values(self):
        res = super().set_values()
        parameter = self.env["ir.config_parameter"].sudo()
        parameter.set_param(
            "tms_account.tms_analytic_plan_ids", self.tms_analytic_plan.ids
        )
        return res

    @api.depends("tms_analytic_plan")
    def _compute_tms_analytic_groups(self):
        for record in self:
            record.group_tms_route_analytic_plan = False
            record.group_tms_order_analytic_plan = False

            for plan in record.tms_analytic_plan:
                if plan == self.env.ref("tms_account.tms_route_analytic_plan"):
                    record.group_tms_route_analytic_plan = True
                if plan == self.env.ref("tms_account.tms_order_analytic_plan"):
                    record.group_tms_order_analytic_plan = True
