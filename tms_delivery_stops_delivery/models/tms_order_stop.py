# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class TMSOrderStop(models.Model):
    _inherit = "tms.order.stop"

    order_id = fields.Many2one(
        comodel_name="tms.order",
        string="Order",
        required=False,
        ondelete="cascade",
    )
    picking_id = fields.Many2one(
        comodel_name="stock.picking",
        string="Picking",
        ondelete="set null",
    )
    sale_order_id = fields.Many2one(
        comodel_name="sale.order",
        string="Sales Order",
        related="picking_id.sale_id",
        store=False,
        readonly=True,
    )
    picking_name = fields.Char(
        string="Picking Reference",
        related="picking_id.name",
        store=False,
        readonly=True,
    )
