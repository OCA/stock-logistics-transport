# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command, api, fields, models
from odoo.exceptions import ValidationError


class ShipmentAdvicePlanner(models.TransientModel):
    _name = "shipment.advice.planner"
    _description = "Shipment Advice Planner"

    picking_to_plan_ids = fields.Many2many(
        comodel_name="stock.picking",
        string="Pickings to plan",
        required=True,
        domain='[("can_be_planned_in_shipment_advice", "=", True),'
        '("picking_type_id.warehouse_id", "=?", warehouse_id),]',
        compute="_compute_picking_to_plan_ids",
        store=True,
        readonly=False,
    )
    shipment_planning_method = fields.Selection(
        selection=[("simple", "Simple")], required=True, default="simple"
    )
    warehouse_id = fields.Many2one(comodel_name="stock.warehouse")
    dock_id = fields.Many2one(
        comodel_name="stock.dock", domain='[("warehouse_id", "=", warehouse_id)]'
    )

    @api.constrains("warehouse_id", "dock_id", "picking_to_plan_ids")
    def _check_warehouse(self):
        for rec in self:
            if not rec.warehouse_id:
                continue
            if rec.dock_id and rec.dock_id.warehouse_id != rec.warehouse_id:
                raise ValidationError(
                    self.env._("The dock doesn't belong to the selected warehouse.")
                )
            if (
                rec.picking_to_plan_ids
                and rec.picking_to_plan_ids.picking_type_id.warehouse_id
                != rec.warehouse_id
            ):
                raise ValidationError(
                    self.env._("The transfers don't belong to the selected warehouse.")
                )

    @api.onchange("warehouse_id", "dock_id", "picking_to_plan_ids")
    def _onchange_check_warehouse(self):
        self.ensure_one()
        self._check_warehouse()

    @api.constrains("picking_to_plan_ids")
    def _check_picking_to_plan(self):
        for rec in self:
            if rec.picking_to_plan_ids.filtered(
                lambda p: not p.can_be_planned_in_shipment_advice
            ):
                raise ValidationError(
                    self.env._(
                        "The transfers selected must be ready and of the delivery type."
                    )
                )

    @api.onchange("picking_to_plan_ids")
    def _onchange_check_picking_to_plan(self):
        self.ensure_one()
        self._check_picking_to_plan()

    @api.model
    def _get_compute_picking_to_plan_ids_depends(self):
        return ["shipment_planning_method", "warehouse_id"]

    @api.depends_context("active_model", "active_ids")
    @api.depends(lambda m: m._get_compute_picking_to_plan_ids_depends())
    def _compute_picking_to_plan_ids(self):
        """meant to be inherited if for specific method picking to plan should have
        a default record set"""
        active_model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids")
        if not active_ids or active_model != "stock.picking":
            return self.update({"picking_to_plan_ids": False})
        pickings_to_plan = self.env[active_model].search(
            [
                ("id", "in", active_ids),
                ("can_be_planned_in_shipment_advice", "=", True),
                ("picking_type_id.warehouse_id", "=?", self.warehouse_id.id),
            ]
        )

        return self.update({"picking_to_plan_ids": [Command.set(pickings_to_plan.ids)]})

    def button_plan_shipments(self):
        self.ensure_one()
        shipment_advices = self._plan_shipments_for_method()
        if not shipment_advices:
            return {}
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Shipment Advice"),
            "view_mode": "list,form",
            "res_model": shipment_advices._name,
            "domain": [("id", "in", shipment_advices.ids)],
            "context": self.env.context,
        }

    def _plan_shipments_for_method(self):
        self.ensure_one()
        prepare_method_name = self._get_prepare_method_name()
        if not hasattr(self, prepare_method_name):
            raise NotImplementedError(
                self.env._("There is no implementation for the planning method '%s'")
                % self.shipment_planning_method
            )
        prepare_method = getattr(self, prepare_method_name)
        shipment_advice_model = self.env["shipment.advice"]
        create_vals = []
        for (
            picking_type,
            pickings_to_plan,
        ) in self._get_picking_to_plan_by_picking_type().items():
            create_vals.extend(prepare_method(picking_type, pickings_to_plan))
        return shipment_advice_model.create(create_vals)

    def _get_prepare_method_name(self):
        self.ensure_one()
        return f"_prepare_shipment_advice_{self.shipment_planning_method}_vals_list"

    def _get_picking_to_plan_by_picking_type(self):
        self.ensure_one()
        picking_type_model = self.env["stock.picking.type"]
        picking_model = self.env["stock.picking"]
        res = {}
        for group in picking_model.read_group(
            [("id", "in", self.picking_to_plan_ids.ids)],
            ["picking_type_id"],
            ["picking_type_id"],
        ):
            picking_type = picking_type_model.browse(group.get("picking_type_id")[0])
            res[picking_type] = picking_model.search(group.get("__domain"))
        return res

    def _prepare_shipment_advice_simple_vals_list(self, picking_type, pickings_to_plan):
        self.ensure_one()
        vals = self._prepare_shipment_advice_common_vals(picking_type)
        vals["planned_move_ids"] = [Command.set(pickings_to_plan.move_ids.ids)]
        return [vals]

    def _prepare_shipment_advice_common_vals(self, picking_type):
        self.ensure_one()
        return {
            "shipment_type": "outgoing",
            "warehouse_id": picking_type.warehouse_id.id,
            "dock_id": self.dock_id.id,
            "company_id": picking_type.company_id.id,
            "arrival_date": fields.Datetime.now(),
            "departure_date": fields.Datetime.now(),
            "state": "confirmed",
        }
