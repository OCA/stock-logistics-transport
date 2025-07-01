# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import Form

from odoo.addons.base.tests.common import BaseCommon


class TestShipmentAdvicePlannerCommon(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env.ref("stock.warehouse0")
        customer_location = cls.env["stock.location"].search(
            [("usage", "=", "customer")], limit=1
        )
        partner = cls.env["res.partner"].create({"name": "Test Warehouse Partner"})
        # Create second warehouse
        cls.warehouse2 = cls.env["stock.warehouse"].create(
            {
                "name": "Test Warehouse 2",
                "code": "TST2",
                "partner_id": partner.id,
                "company_id": cls.env.ref("base.main_company").id,
            }
        )
        # Create outgoing picking type for warehouse2
        picking_type_out2 = cls.env["stock.picking.type"].create(
            {
                "name": "TST2: Delivery Orders",
                "code": "outgoing",
                "warehouse_id": cls.warehouse2.id,
                "sequence_code": "TST2_OUT",
                "default_location_src_id": cls.warehouse2.lot_stock_id.id,
                "default_location_dest_id": customer_location.id,
            }
        )
        product = cls.env["product.product"].create(
            {
                "name": "Test Product",
                "type": "consu",
                "is_storable": True,
            }
        )
        cls.env["stock.quant"].create(
            {
                "product_id": product.id,
                "location_id": cls.warehouse2.lot_stock_id.id,
                "quantity": 10.0,
            }
        )
        picking = cls.env["stock.picking"].create(
            {
                "partner_id": partner.id,
                "picking_type_id": picking_type_out2.id,
                "location_id": picking_type_out2.default_location_src_id.id,
                "location_dest_id": picking_type_out2.default_location_dest_id.id,
            }
        )

        cls.env["stock.move"].create(
            {
                "name": product.name,
                "product_id": product.id,
                "product_uom_qty": 5.0,
                "product_uom": product.uom_id.id,
                "picking_id": picking.id,
                "location_id": picking.location_id.id,
                "location_dest_id": picking.location_dest_id.id,
            }
        )
        picking.action_assign()
        cls.pickings = cls.env["stock.picking"].search([])
        cls.context = {
            "active_ids": cls.pickings.ids,
            "active_model": "stock.picking",
        }
        cls.dock = cls.env.ref("shipment_advice.stock_dock_demo")

    def setUp(self):
        super().setUp()
        self.wizard_form = Form(
            self.env["shipment.advice.planner"].with_context(**self.context)
        )
