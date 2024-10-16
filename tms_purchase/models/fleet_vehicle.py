from odoo import _, fields, models


class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle"

    purchase_order_id = fields.Many2one("purchase.order")

    def action_view_order(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "purchase.order",
            "view_mode": "form",
            "res_id": self.purchase_order_id.id,
            "target": "current",
            "name": _("Purchase order: %s") % self.purchase_order_id.name,
        }
