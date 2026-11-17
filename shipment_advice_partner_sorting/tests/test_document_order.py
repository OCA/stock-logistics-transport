# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
from unittest.mock import patch

from odoo.addons.shipment_advice.tests.common import Common


class TestDocumentOrder(Common):
    def _prepare_documents(self):
        shipment = self.shipment_advice_out
        picking1 = self.move_product_out1.picking_id
        self._update_qty_in_location(
            self.picking_type_out.default_location_src_id, self.product_out1, 25
        )
        picking2 = self._create_distinct_picking(
            self.picking_type_out, self.product_out1, 2
        )
        second_move = self._create_move(
            self.picking_type_out,
            self.product_out1,
            1,
            picking2.group_id,
            picking2.partner_id,
        )
        self.assertEqual(second_move.picking_id, picking2)
        picking2._put_in_pack(second_move.move_line_ids)
        self.plan_records_in_shipment(shipment, picking1 | picking2)
        self.progress_shipment_advice(shipment)
        self.load_records_in_shipment(shipment, picking1 | picking2)
        self.assertEqual(len(shipment.loaded_package_level_ids), 2)
        self.assertEqual(
            set(shipment.loaded_move_line_without_package_ids.picking_id.ids),
            {picking1.id, picking2.id},
        )
        return shipment, picking1, picking2

    def _assert_document_order(self, shipment, first, second):
        self.assertEqual(
            shipment._get_email_planned_pickings().ids, [first.id, second.id]
        )
        report_model = self.env["report.shipment_advice.report_shipment_advice"]
        self.assertEqual(
            report_model._get_package_levels(shipment).picking_id.ids,
            [first.id, second.id],
        )
        self.assertEqual(
            report_model._get_bulk_move_lines(shipment).picking_id.ids,
            [first.id, second.id],
        )
        report_class = type(report_model)
        with (
            patch.object(
                report_class,
                "_get_package_levels",
                autospec=True,
                side_effect=report_class._get_package_levels,
            ) as packages,
            patch.object(
                report_class,
                "_get_bulk_move_lines",
                autospec=True,
                side_effect=report_class._get_bulk_move_lines,
            ) as lines,
        ):
            report = shipment.env.ref("shipment_advice.action_report_shipment_advice")
            report._render_qweb_html(report.report_name, [shipment.id])
            packages.assert_called_once()
            lines.assert_called_once()
            self.assertEqual(packages.call_args.args[1], shipment)
            self.assertEqual(lines.call_args.args[1], shipment)

    def test_document_order_respects_partner_sorting(self):
        shipment, picking1, picking2 = self._prepare_documents()
        self._assert_document_order(shipment, picking1, picking2)

        shipment.partner_sorting_enabled = True
        shipment.planned_partner_order_ids.filtered(
            lambda order: picking1 in order.stock_picking_ids
        ).sequence = 20
        shipment.planned_partner_order_ids.filtered(
            lambda order: picking2 in order.stock_picking_ids
        ).sequence = 5
        other = self.env["shipment.advice"].create({"shipment_type": "outgoing"})
        self._assert_document_order(
            shipment.with_context(active_shipment_advice_id=other.id),
            picking2,
            picking1,
        )

        shipment.partner_sorting_enabled = False
        self._assert_document_order(shipment, picking1, picking2)
