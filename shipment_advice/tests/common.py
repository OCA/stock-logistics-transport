# Copyright 2021 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import fields
from odoo.tests.common import SavepointCase


class Common(SavepointCase):
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
            cls.picking_type_out.default_location_src_id, cls.product_out1, 20,
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

    def _confirm_shipment_advice(self, shipment_advice, arrival_date=None):
        if shipment_advice.state != "draft":
            return
        if arrival_date is None:
            arrival_date = fields.Datetime.now()
        shipment_advice.arrival_date = arrival_date
        shipment_advice.action_confirm()
        self.assertEqual(shipment_advice.state, "confirmed")

    def _in_progress_shipment_advice(self, shipment_advice, dock=None):
        self._confirm_shipment_advice(shipment_advice)
        if shipment_advice.state != "confirmed":
            return
        shipment_advice.dock_id = dock or self.dock
        shipment_advice.action_in_progress()
        self.assertEqual(shipment_advice.state, "in_progress")

    def _cancel_shipment_advice(self, shipment_advice, dock=None):
        self._confirm_shipment_advice(shipment_advice)
        if shipment_advice.state != "confirmed":
            return
        shipment_advice.action_cancel()
        self.assertEqual(shipment_advice.state, "cancel")

    def _plan_records_in_shipment(self, shipment_advice, records):
        wiz_model = self.env["wizard.plan.shipment"].with_context(
            active_model=records._name, active_ids=records.ids,
        )
        wiz = wiz_model.create({"shipment_advice_id": shipment_advice.id})
        wiz.action_plan()
        return wiz

    def _load_records_in_shipment(self, shipment_advice, records):
        """Load pickings, move lines or package levels in the givent shipment."""
        wiz_model = self.env["wizard.load.shipment"].with_context(
            active_model=records._name, active_ids=records.ids,
        )
        wiz = wiz_model.create({"shipment_advice_id": shipment_advice.id})
        wiz.action_load()
        return wiz

    def _unload_records_from_shipment(self, shipment_advice, records):
        """Unload pickings, move lines or package levels from the givent shipment."""
        wiz_model = self.env["wizard.unload.shipment"].with_context(
            active_model=records._name, active_ids=records.ids,
        )
        wiz = wiz_model.create({})
        wiz.action_unload()
        return wiz
