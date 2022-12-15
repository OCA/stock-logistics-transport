# Copyright 2021 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class WizardUnplanShipment(models.TransientModel):
    _name = "wizard.unplan.shipment"
    _description = "Unplan shipment"

    picking_ids = fields.Many2many(
        comodel_name="stock.picking",
        string="Transfers to unplan",
    )
    move_ids = fields.Many2many(
        comodel_name="stock.move",
        string="Moves to unplan",
    )
    warning = fields.Char(readonly=True)

    @api.model
    def default_get(self, fields_list):
        """'default_get' method overloaded."""
        res = super().default_get(fields_list)
        active_model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids")
        if not active_ids:
            raise UserError(
                _("Please select at least one record to unplan from shipment.")
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
        pickings_to_keep = pickings.filtered(
            lambda o: (
                o.state not in ["cancel", "done"]
                and o.move_ids.shipment_advice_id
                and all(
                    state in ("draft", "confirmed")
                    for state in o.move_ids.shipment_advice_id.mapped("state")
                )
                and o.picking_type_code in ("incoming", "outgoing")
            )
        )
        res["picking_ids"] = [(6, False, pickings_to_keep.ids)]
        if not pickings_to_keep:
            res["warning"] = _(
                "No transfer to unplan among selected ones (already done or "
                "not related to a shipment)."
            )
        elif pickings != pickings_to_keep:
            res["warning"] = _(
                "Transfers to include have been updated, keeping only those "
                "still in progress and related to a shipment."
            )
        return res

    @api.model
    def _default_get_from_stock_move(self, res, ids):
        moves = self.env["stock.move"].browse(ids)
        # We keep only deliveries and receptions not canceled/done
        # and not linked to a package level itself linked to other moves
        # (we want to unplan the package as a whole, not a part of it)
        moves_to_keep = self.env["stock.move"]
        for move in moves:
            other_moves = (
                move.move_line_ids.package_level_id.move_line_ids.move_id
                + move.package_level_id.move_ids
            ) - move
            if other_moves:
                continue
            moves_to_keep |= move
        moves_to_keep = moves_to_keep.filtered_domain(
            [
                ("state", "not in", ["cancel", "done"]),
                ("shipment_advice_id", "!=", False),
                ("shipment_advice_id.state", "in", ("draft", "confirmed")),
            ]
        )
        res["move_ids"] = [(6, False, moves_to_keep.ids)]
        if not moves_to_keep:
            res["warning"] = _(
                "No move to unplan among selected ones (already done, "
                "linked to other moves through a package, or not related "
                "to a shipment)."
            )
        elif moves != moves_to_keep:
            res["warning"] = _(
                "Moves to include have been updated, keeping only those "
                "still in progress and related to a shipment."
            )
        return res

    def action_unplan(self):
        """Unplan the selected records from their related shipment."""
        self.ensure_one()
        self.picking_ids.move_ids.shipment_advice_id = False
        self.move_ids.shipment_advice_id = False
        return True
