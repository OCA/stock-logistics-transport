# Copyright 2024 Camptocamp SA
# Copyright 2024 Michael Tietz (MT Software) <mtietz@mt-software.de>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models


class ShipmentAdvice(models.Model):
    _inherit = "shipment.advice"

    supplier_ids = fields.Many2many(
        comodel_name="res.partner",
        compute="_compute_supplier_ids",
        store=True,
        copy=False,
    )
    account_move_id = fields.Many2one(
        comodel_name="account.move",
        compute="_compute_account_move_id",
        store=True,
        copy=False,
    )
    invoice_line_ids = fields.One2many(
        "account.move.line",
        "shipment_advice_id",
        string="Bill Lines",
        readonly=True,
        copy=False,
    )

    @api.depends("planned_move_ids.picking_id.partner_id", "state", "shipment_type")
    def _compute_supplier_ids(self):
        for shipment in self:
            supplier_ids = False
            if shipment.shipment_type == "incoming":
                supplier_ids = shipment.planned_move_ids.picking_id.partner_id
            shipment.supplier_ids = supplier_ids

    @api.depends("invoice_line_ids")
    def _compute_account_move_id(self):
        for shipment in self:
            shipment.account_move_id = fields.first(shipment.invoice_line_ids).move_id
