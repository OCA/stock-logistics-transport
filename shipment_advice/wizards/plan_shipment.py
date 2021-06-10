# Copyright 2021 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class WizardPlanShipment(models.TransientModel):
    _name = "wizard.plan.shipment"
    _description = "Plan shipment"

    picking_ids = fields.Many2many(
        comodel_name="stock.picking", string="Transfers to plan",
    )
    move_ids = fields.Many2many(comodel_name="stock.move", string="Moves to plan",)
    shipment_advice_id = fields.Many2one(
        comodel_name="shipment.advice",
        string="Shipment Advice",
        required=True,
        domain=[("state", "in", ("draft", "confirmed"))],
    )
    warning = fields.Char(string="Warning", readonly=True)

    @api.model
    def default_get(self, fields_list):
        """'default_get' method overloaded."""
        res = super().default_get(fields_list)
        active_model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids")
        if not active_ids:
            raise UserError(
                _("Please select at least one record to plan in a shipment.")
            )
        if active_model == "stock.picking" and active_ids:
            res = self._default_get_from_stock_picking(res, active_ids)
        if active_model == "stock.move" and active_ids:
            res = self._default_get_from_stock_move(res, active_ids)
        return res

    @api.model
    def _default_get_from_stock_picking(self, res, ids):
        pickings = self.env["stock.picking"].browse(ids)
        # We keep only deliveries and receptions not canceled/done
        pickings_to_keep = pickings.filtered_domain(
            [
                ("state", "not in", ["cancel", "done"]),
                ("picking_type_code", "in", ["incoming", "outgoing"]),
            ]
        )
        res["picking_ids"] = pickings_to_keep.ids
        if not pickings_to_keep:
            res["warning"] = _(
                "No transfer to plan among selected ones (already done or "
                "not qualified as deliveries/receptions)."
            )
        elif pickings != pickings_to_keep:
            res["warning"] = _(
                "Transfers to include have been updated, keeping only those "
                "still in progress and qualified as delivery/reception."
            )
        return res

    @api.model
    def _default_get_from_stock_move(self, res, ids):
        moves = self.env["stock.move"].browse(ids)
        # We keep only deliveries and receptions not canceled/done
        # and not linked to a package level itself linked to other moves
        # (we want to plan the package as a whole, not a part of it)
        moves_to_keep = self.env["stock.move"]
        for move in moves:
            other_moves = (
                move.move_line_ids.package_level_id.move_line_ids.move_id
                + move.package_level_id.move_ids
            ) - moves
            if other_moves:
                continue
            moves_to_keep |= move
        moves_to_keep = moves_to_keep.filtered_domain(
            [
                ("state", "not in", ["cancel", "done"]),
                ("picking_type_id.code", "in", ["incoming", "outgoing"]),
            ]
        )
        res["move_ids"] = moves_to_keep.ids
        if not moves_to_keep:
            res["warning"] = _(
                "No move to plan among selected ones (already done, "
                "linked to other moves through a package, or not related "
                "to a delivery/reception)."
            )
        elif moves != moves_to_keep:
            res["warning"] = _(
                "Moves to include have been updated, keeping only those "
                "still in progress and related to a delivery/reception."
            )
        return res

    @api.onchange("shipment_advice_id")
    def _onchange_shipment_advice_id(self):
        if not self.shipment_advice_id:
            return
        pickings = self.picking_ids.filtered(
            lambda o: o.picking_type_code == self.shipment_advice_id.shipment_type
        )
        moves = self.move_ids.filtered(
            lambda o: o.picking_type_id.code == self.shipment_advice_id.shipment_type
        )
        res = {}
        if self.picking_ids != pickings:
            res.update(
                warning={
                    "title": _("Transfers updated"),
                    "message": _(
                        "Transfers to include have been updated "
                        "to match the selected shipment type."
                    ),
                }
            )
        if self.move_ids != moves:
            res.update(
                warning={
                    "title": _("Moves updated"),
                    "message": _(
                        "Moves to include have been updated "
                        "to match the selected shipment type."
                    ),
                }
            )
        self.picking_ids = pickings
        self.move_ids = moves
        return res

    def action_plan(self):
        """Plan the selected records in the selected shipment."""
        self.ensure_one()
        self.picking_ids._plan_in_shipment(self.shipment_advice_id)
        self.move_ids._plan_in_shipment(self.shipment_advice_id)
        view_form = self.env.ref("shipment_advice.shipment_advice_view_form")
        action = self.env.ref("shipment_advice.shipment_advice_action").read()[0]
        del action["views"]
        action["res_id"] = self.shipment_advice_id.id
        action["view_id"] = view_form.id
        action["view_mode"] = "form"
        return action
