# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
from odoo.addons.shipment_advice.tests.common import Common


class ShipmentAdviceSearchCommonCase(Common):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.picking1 = cls.move_product_out1.picking_id
        cls.picking2 = cls._create_distinct_picking(
            cls.picking_type_out, cls.product_out2, 5
        )
        cls.picking3 = cls._create_distinct_picking(
            cls.picking_type_out, cls.product_out3, 5
        )
        cls.other_shipment = cls.env["shipment.advice"].create(
            {"shipment_type": "outgoing"}
        )
        cls.partner1, cls.partner2 = cls.env["res.partner"].create(
            [{"name": "Sorting partner 1"}, {"name": "Sorting partner 2"}]
        )
        cls.planned_orders = cls.env["shipment.advice.planned.partner.order"].create(
            [
                {
                    "shipment_advice_id": cls.shipment_advice_out.id,
                    "partner_id": cls.partner1.id,
                    "stock_picking_ids": [(6, 0, cls.picking1.ids)],
                    "sequence": 20,
                },
                {
                    "shipment_advice_id": cls.shipment_advice_out.id,
                    "partner_id": cls.partner2.id,
                    "stock_picking_ids": [(6, 0, cls.picking2.ids)],
                    "sequence": 10,
                },
                {
                    "shipment_advice_id": cls.other_shipment.id,
                    "stock_picking_ids": [(6, 0, (cls.picking1 | cls.picking2).ids)],
                    "sequence": 5,
                },
            ]
        )
