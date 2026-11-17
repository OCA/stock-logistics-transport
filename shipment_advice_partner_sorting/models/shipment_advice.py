# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
from odoo import Command, api, fields, models


class ShipmentAdvice(models.Model):
    _inherit = "shipment.advice"

    partner_sorting_enabled = fields.Boolean(string="Order by Partner", default=False)
    planned_partner_order_ids = fields.One2many(
        "shipment.advice.planned.partner.order",
        "shipment_advice_id",
        string="Planned Partners Sequence",
        compute="_compute_planned_partner_order_ids",
        store=True,
    )
    planned_partners_count = fields.Integer(compute="_compute_planned_partners_count")

    @api.depends("planned_partner_order_ids")
    def _compute_planned_partners_count(self):
        for shipment in self:
            shipment.planned_partners_count = len(shipment.planned_partner_order_ids)

    @api.depends(
        "partner_sorting_enabled",
        "planned_move_ids.picking_id",
        "planned_move_ids.picking_id.partner_id",
    )
    def _compute_planned_partner_order_ids(self):
        order_model = self.env["shipment.advice.planned.partner.order"]
        for shipment in self:
            if not shipment.partner_sorting_enabled:
                shipment.planned_partner_order_ids.unlink()
                shipment.planned_partner_order_ids = False
                continue
            planned_by_key = {}
            for picking in shipment.planned_picking_ids:
                key = ("partner", picking.partner_id.id or False)
                planned_by_key.setdefault(key, self.env["stock.picking"])
                planned_by_key[key] |= picking

            existing_by_key = {}
            obsolete_orders = order_model
            for order in shipment.planned_partner_order_ids:
                key = order._get_planned_order_key()
                if not key or key in existing_by_key:
                    obsolete_orders |= order
                else:
                    existing_by_key[key] = order
            for key, order in existing_by_key.items():
                if key not in planned_by_key:
                    obsolete_orders |= order
            obsolete_orders.unlink()

            commands = []
            for key, pickings in planned_by_key.items():
                order = existing_by_key.get(key)
                if order:
                    order.stock_picking_ids = [Command.set(pickings.ids)]
                    commands.append(Command.link(order.id))
                else:
                    commands.append(
                        Command.create(
                            {
                                "partner_id": key[1],
                                "stock_picking_ids": [Command.set(pickings.ids)],
                            }
                        )
                    )
            shipment.planned_partner_order_ids = commands

    def _sort_by_partner_sequence(self, records, get_picking):
        self.ensure_one()
        if not self.partner_sorting_enabled:
            return records
        contextual_records = records.with_context(active_shipment_advice_id=self.id)
        sorted_records = contextual_records.sorted(
            lambda record: get_picking(record).sequence_in_shipment_advice
        )
        return records.browse(sorted_records.ids)

    def _get_email_planned_pickings(self):
        return self._sort_by_partner_sequence(
            super()._get_email_planned_pickings(), lambda picking: picking
        )

    def button_open_planned_partners(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "shipment_advice_partner_sorting.action_shipment_advice_planned_partner_order"
        )
        action["domain"] = [("shipment_advice_id", "=", self.id)]
        return action

    def button_open_planned_pickings(self):
        action = super().button_open_planned_pickings()
        if self.partner_sorting_enabled:
            tree_view = self.env.ref(
                "shipment_advice_partner_sorting.vpicktree_planned_shipment_advice_order"
            )
            index = action["views"].index((False, "tree"))
            action["views"][index] = (tree_view.id, "tree")
        return action

    def button_open_planned_moves(self):
        action = super().button_open_planned_moves()
        if self.partner_sorting_enabled:
            tree_view = self.env.ref(
                "shipment_advice_partner_sorting.view_picking_move_tree_sorting"
            )
            action["views"] = [(tree_view.id, "tree")]
        return action
