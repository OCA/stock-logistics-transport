# Copyright 2024 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class WizardPlanReceptionShipment(models.TransientModel):
    _name = "wizard.plan.reception.shipment"
    _description = "Plan Reception shipment"

    move_ids = fields.Many2many(
        comodel_name="stock.move",
        domain=lambda self: self._get_stock_move_domain(),
        string="Moves Being Planned",
    )
    shipment_advice_id = fields.Many2one(
        comodel_name="shipment.advice",
        string="Shipment Advice",
        required=True,
    )
    warehouse_id = fields.Many2one(related="shipment_advice_id.warehouse_id")
    move_to_split_ids = fields.Many2many(comodel_name="wizard.stock.move.split")

    @api.onchange("move_ids")
    def onchange_quantity_to_split_wizard(self):
        self.move_to_split_ids = [(5, 0, 0)]
        for move in self.move_ids:
            if move.quantity_to_split_wizard:
                self.move_to_split_ids = [
                    (
                        0,
                        0,
                        {
                            "move_id": move.id,
                            "quantity_to_split": move.quantity_to_split_wizard,
                        },
                    )
                ]
        return

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get("active_ids")
        # Check shipment advice used for planning the reception
        shipment_id = False
        if active_ids:
            shipment_id = active_ids[0]
        shipment = self.env["shipment.advice"].browse(shipment_id)
        if not shipment.exists():
            raise UserError(_("No shipment advice found to plan the reception!"))
        if shipment.shipment_type != "incoming":
            raise UserError(
                _("Only an incoming shipment can be used to plan a reception!")
            )
        if not shipment.arrival_date:
            raise UserError(
                _(
                    "Please set an arrival date on the shipment before planning. "
                    "It can still be changed later."
                )
            )
        res["shipment_advice_id"] = shipment_id
        return res

    def _get_stock_move_domain(self):
        """Domain to filter the selectable stock moves."""
        return [
            ("picking_code", "=", "incoming"),
            ("state", "=", "assigned"),
            ("shipment_advice_id", "=", False),
            ("warehouse_id", "=", self.warehouse_id.id),
        ]

    def _prepare_move_split_vals(self, move, split_qty):
        split_qty_uom = move.product_id.uom_id._compute_quantity(
            split_qty, move.product_uom, rounding_method="HALF-UP"
        )
        return move._prepare_move_split_vals(split_qty_uom)

    def _split_move(self, move, split_qty):
        split_move = move.copy(self._prepare_move_split_vals(move, split_qty))
        new_product_qty = move.product_id.uom_id._compute_quantity(
            move.product_qty - split_qty, move.product_uom, round=False
        )
        move.product_uom_qty = new_product_qty
        return split_move

    def action_plan_reception(self):
        """Plan the selected moves in the shipment advice."""
        self.ensure_one()
        for move_to_split in self.move_to_split_ids:
            new_move = self._split_move(
                move_to_split.move_id, move_to_split.quantity_to_split
            )
            self.move_ids -= move_to_split.move_id
            self.move_ids |= new_move
        if self.move_ids:
            self.move_ids._plan_in_shipment(self.shipment_advice_id)
            self.move_ids.write({"date": self.shipment_advice_id.arrival_date})
        view_form = self.env.ref("shipment_advice.shipment_advice_view_form")
        action_xmlid = "shipment_advice.shipment_advice_action"
        action = self.env["ir.actions.act_window"]._for_xml_id(action_xmlid)
        del action["views"]
        action["res_id"] = self.shipment_advice_id.id
        action["view_id"] = view_form.id
        action["view_mode"] = "form"
        return action
