# Copyright (C) 2024 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import _, api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"
    trip_id = fields.Many2one("tms.order")
    vehicle_ids = fields.One2many("fleet.vehicle", "purchase_order_id")
    vehicle_count = fields.Integer(compute="_compute_vehicle_count", readonly=True)

    order_vehicle_count = fields.Integer(
        compute="_compute_order_vehicle_count",
        string="Vehicle Count",
        copy=False,
        default=0,
        store=True,
    )

    @api.depends("vehicle_ids")
    def _compute_order_vehicle_count(self):
        for order in self:
            order.order_vehicle_count = len(order.vehicle_ids)

    def action_view_order(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "tms.order",
            "view_mode": "form",
            "res_id": self.trip_id.id,
            "target": "current",
            "name": _("Trip: %s") % self.trip_id.name,
        }

    def action_view_vehicle(self, vehicles=False):
        """This function returns an action that display existing vehicles from
        given purchase order ids. When only one found, show the vehicle immediately.
        """

        if not vehicles:
            self.invalidate_model(["vehicle_ids"])
            vehicles = self.vehicle_ids

        result = self.env["ir.actions.act_window"]._for_xml_id(
            "fleet.fleet_vehicle_action"
        )

        if len(vehicles) > 1:
            result["domain"] = [("id", "in", vehicles.ids)]
        elif len(vehicles) == 1:
            vehicle_id = vehicles.id
            result = {
                "type": "ir.actions.act_window",
                "name": "Vehicle",
                "res_model": "fleet.vehicle",
                "res_id": vehicle_id,
                "view_mode": "form",
                "view_id": self.env.ref("fleet.fleet_vehicle_view_form").id,
                "target": "current",
            }
        else:
            result = {"type": "ir.actions.act_window_close"}

        return result

    @api.model
    def action_view_vehicles_button(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "fleet.vehicle",
            "view_mode": "tree,form",
            "domain": [("purchase_order_id", "=", self.id)],
            "context": {"default_order_id": self.id},
            "name": _("Vehicles from purchase order %s") % self.name,
        }

    @api.depends("vehicle_ids")
    def _compute_vehicle_count(self):
        for record in self:
            record.vehicle_count = len(record.vehicle_ids)
