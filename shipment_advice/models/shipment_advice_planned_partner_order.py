# Copyright 2021 Camptocamp SA
# Copyright 2024 Michael Tietz (MT Software) <mtietz@mt-software.de>
# Copyright 2025 Jacques-Etienne Baudoux (BCIM) <je@bcim.be>
# Copyright 2026 ACSONE SA/NV (https://acsone.eu)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import fields, models


class ShipmentAdvicePlannedPartnerOrder(models.Model):
    _name = "shipment.advice.planned.partner.order"
    _description = "Shipment Advice Planned Partner Order"
    _order = "shipment_advice_id, sequence"
    _check_company_auto = True

    shipment_advice_id = fields.Many2one(
        comodel_name="shipment.advice",
        string="Shipment Advice",
        required=True,
        ondelete="cascade",
        index=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Partner",
        ondelete="cascade",
        check_company=True,
        index=True,
    )
    operation_type = fields.Selection(
        selection=[
            ("pickup", "Pickup"),
            ("delivery", "Delivery"),
        ]
    )
    stock_picking_ids = fields.Many2many(
        comodel_name="stock.picking",
        string="Planned Transfers",
        relation="shipment_advice_planned_partner_order_stock_picking_rel",
        column1="shipment_advice_planned_partner_order_id",
        column2="stock_picking_id",
        required=True,
        check_company=True,
        index=True,
    )
    sequence = fields.Integer(default=0)
    company_id = fields.Many2one(
        related="shipment_advice_id.company_id",
        store=True,
        readonly=True,
    )

    _sql_constraints = [
        (
            "shipment_advice_planned_partner_operation_uniq",
            "unique(shipment_advice_id, partner_id, operation_type)",
            "A partner and operation type can only be planned once per shipment advice.",
        ),
    ]
