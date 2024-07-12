# Copyright 2021 Camptocamp SA
# Copyright 2024 Michael Tietz (MT Software) <mtietz@mt-software.de>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import fields
from odoo.tests.common import Form, TransactionCase, new_test_user


class Common(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        # Configuration
        cls.dock = cls.env.ref("shipment_advice.stock_dock_demo")
        cls.picking_type_out = cls.env.ref("stock.picking_type_out")
        cls.picking_type_out.default_location_dest_id = cls.env.ref(
            "stock.stock_location_customers"
        )
        cls.picking_type_in = cls.env.ref("stock.picking_type_in")
        cls.picking_type_in.default_location_src_id = cls.env.ref(
            "stock.stock_location_suppliers"
        )
        # Shipment
        cls.shipment_advice_in = cls.env["shipment.advice"].create(
            {"shipment_type": "incoming"}
        )
        cls.shipment_advice_out = cls.env["shipment.advice"].create(
            {"shipment_type": "outgoing"}
        )
        # Products
        cls.product_in = cls.env.ref("product.product_delivery_01")
        cls.product_out1 = cls.env.ref("product.consu_delivery_01")
        cls.product_out2 = cls.env.ref("product.consu_delivery_02")
        cls.product_out3 = cls.env.ref("product.consu_delivery_03")
        # Stock levels
        cls._update_qty_in_location(
            cls.picking_type_out.default_location_src_id,
            cls.product_out1,
            20,
        )
        cls.package = cls.env["stock.quant.package"].create({"name": "PKG_OUT2"})
        cls._update_qty_in_location(
            cls.picking_type_out.default_location_src_id,
            cls.product_out2,
            10,
            package=cls.package,
        )
        cls._update_qty_in_location(
            cls.picking_type_out.default_location_src_id,
            cls.product_out3,
            10,
            package=cls.package,
        )
        # Moves & transfers
        cls.move_product_in1 = cls._create_move(cls.picking_type_in, cls.product_in, 5)
        cls.move_product_in2 = cls._create_move(cls.picking_type_in, cls.product_in, 5)
        cls.group = cls.env["procurement.group"].create({})
        cls.move_product_out1 = cls._create_move(
            cls.picking_type_out, cls.product_out1, 20, cls.group
        )
        cls.move_product_out2 = cls._create_move(
            cls.picking_type_out, cls.product_out2, 10, cls.group
        )
        cls.move_product_out3 = cls._create_move(
            cls.picking_type_out, cls.product_out3, 10, cls.group
        )

    # Inspired by
    # https://github.com/OCA/wms/commit/11730a7119a9695a72ed754e4cf078e56664cd1a
    # https://github.com/OCA/wms/commit/73bd34ea551a45fcfe09396f0e48f1ed47574616

    @classmethod
    def setUpClassUsers(cls):
        cls.stock_user = new_test_user(cls.env, **cls._stock_user_values())
        return cls.stock_user

    @classmethod
    def _stock_user_values(cls):
        return {
            "name": "Pauline Poivraisselle",
            "login": "pauline2",
            "email": "p.p@example.com",
            "groups": "stock.group_stock_user",
        }

    @classmethod
    def _update_qty_in_location(
        cls, location, product, quantity, package=None, lot=None
    ):
        quants = cls.env["stock.quant"]._gather(
            product, location, lot_id=lot, package_id=package, strict=True
        )
        # this method adds the quantity to the current quantity, so remove it
        quantity -= sum(quants.mapped("quantity"))
        cls.env["stock.quant"]._update_available_quantity(
            product, location, quantity, package_id=package, lot_id=lot
        )

    @classmethod
    def _create_move(cls, picking_type, product, quantity, group=False):
        move = cls.env["stock.move"].create(
            {
                "name": product.display_name,
                "product_id": product.id,
                "product_uom_qty": quantity,
                "product_uom": product.uom_id.id,
                "location_id": picking_type.default_location_src_id.id,
                "location_dest_id": picking_type.default_location_dest_id.id,
                "warehouse_id": picking_type.warehouse_id.id,
                "picking_type_id": picking_type.id,
                "group_id": group and group.id or False,
                # "procure_method": "make_to_order",
                # "state": "draft",
            }
        )
        move._assign_picking()
        move._action_confirm(merge=False)
        move.picking_id.action_assign()
        return move

    def _check_sequence(self, shipment_advice):
        if shipment_advice.shipment_type == "outgoing":
            self.assertIn("OUT", shipment_advice.name)
        else:
            self.assertIn("IN", shipment_advice.name)

    @classmethod
    def confirm_shipment_advice(cls, shipment_advice, arrival_date=None):
        if shipment_advice.state != "draft":
            return
        if arrival_date is None:
            arrival_date = fields.Datetime.now()
        shipment_advice.arrival_date = arrival_date
        shipment_advice.action_confirm()

    @classmethod
    def progress_shipment_advice(cls, shipment_advice, dock=None):
        cls.confirm_shipment_advice(shipment_advice)
        if shipment_advice.state != "confirmed":
            return
        shipment_advice.dock_id = dock or cls.dock
        shipment_advice.action_in_progress()

    @classmethod
    def cancel_shipment_advice(cls, shipment_advice, dock=None):
        cls.confirm_shipment_advice(shipment_advice)
        if shipment_advice.state != "confirmed":
            return
        shipment_advice.action_cancel()

    @classmethod
    def plan_records_in_shipment(cls, shipment_advice, records, user=None):
        wiz_model = cls.env["wizard.plan.shipment"].with_context(
            active_model=records._name,
            active_ids=records.ids,
        )
        wiz = wiz_model.create({"shipment_advice_id": shipment_advice.id})
        if user:
            wiz = wiz.with_user(user)
        wiz.action_plan()
        return wiz

    @classmethod
    def unplan_records_from_shipment(cls, records, user=None):
        wiz_model = cls.env["wizard.unplan.shipment"].with_context(
            active_model=records._name,
            active_ids=records.ids,
        )
        wiz = wiz_model.create({})
        if user:
            wiz = wiz.with_user(user)
        wiz.action_unplan()
        return wiz

    @classmethod
    def load_records_in_shipment(cls, shipment_advice, records, user=None):
        """Load pickings, move lines or package levels in the givent shipment."""
        wiz_model = cls.env["wizard.load.shipment"].with_context(
            active_model=records._name,
            active_ids=records.ids,
        )
        wiz = wiz_model.create({"shipment_advice_id": shipment_advice.id})
        if user:
            wiz = wiz.with_user(user)
        wiz.action_load()
        return wiz

    @classmethod
    def unload_records_from_shipment(cls, shipment_advice, records):
        """Unload pickings, move lines or package levels from the givent shipment."""
        wiz_model = cls.env["wizard.unload.shipment"].with_context(
            active_model=records._name,
            active_ids=records.ids,
        )
        wiz = wiz_model.create({})
        wiz.action_unload()
        return wiz

    @classmethod
    def validate_picking(cls, picking, qty_done=None):
        picking.ensure_one()
        for ml in picking.move_line_ids:
            ml.qty_done = qty_done or ml.reserved_uom_qty
        action_data = picking.button_validate()
        if action_data is True:
            return cls.env["stock.picking"]
        backorder_wizard = Form(
            cls.env["stock.backorder.confirmation"].with_context(
                **action_data["context"]
            )
        ).save()
        backorder_wizard.process()
        return cls.env["stock.picking"].search([("backorder_id", "=", picking.id)])
