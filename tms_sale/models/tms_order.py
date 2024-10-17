# Copyright (C) 2019 Brian McMaster
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models


class TMSOrder(models.Model):
    _inherit = "tms.order"

    sale_id = fields.Many2one("sale.order", copy=False)
    sale_line_id = fields.Many2one("sale.order.line", copy=False)
    seat_ticket_ids = fields.One2many("seat.ticket", "tms_order_id")

    def action_view_sales(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "views": [[False, "form"]],
            "res_id": self.sale_line_id.order_id.id or self.sale_id.id,
            "context": {"create": False},
            "name": _("Sales Orders"),
        }

    @api.model
    def write(self, vals):
        for order in self:
            if "stage_id" in vals:
                stage = self.env.ref("tms.tms_stage_order_completed")
                if vals["stage_id"] == stage.id:
                    for line in order.sale_id.order_line:
                        line.qty_delivered = line.product_uom_qty

            if "seat_ticket_ids" in vals:
                tickets = vals.get("seat_ticket_ids", [])
                for i in range(len(tickets)):
                    if tickets[i][0] == 2:
                        self.env["seat.ticket"].browse(tickets[i][1]).unlink()

        return super().write(vals)
