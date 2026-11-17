# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
from lxml import html

from .common import Common


class TestShipmentAdviceDocuments(Common):
    def test_report_and_email_without_partner_sorting(self):
        shipment = self.shipment_advice_out
        picking = self.move_product_out1.picking_id
        picking.origin = "DOCUMENT-BASE"
        self.plan_records_in_shipment(shipment, picking)
        self.progress_shipment_advice(shipment)
        self.load_records_in_shipment(shipment, picking)

        self.assertEqual(shipment._get_email_planned_pickings(), picking)
        report_model = self.env["report.shipment_advice.report_shipment_advice"]
        self.assertEqual(report_model._get_package_levels(shipment).picking_id, picking)
        self.assertEqual(
            report_model._get_bulk_move_lines(shipment).picking_id, picking
        )
        template = self.env.ref("shipment_advice.email_template_shipment_advice")
        body = template._render_field("body_html", [shipment.id])[shipment.id]
        self.assertIn("DOCUMENT-BASE", body)
        report = self.env.ref("shipment_advice.action_report_shipment_advice")
        rendered, _ = report._render_qweb_html(report.report_name, [shipment.id])
        tree = html.fromstring(rendered)
        for name in ("package_content", "bulk_content"):
            table = tree.xpath(f"//table[@name='{name}']")[0]
            self.assertIn(picking.name, table.text_content())
        second = self.shipment_advice_in
        rendered, _ = report._render_qweb_html(
            report.report_name, (shipment | second).ids
        )
        tree = html.fromstring(rendered)
        self.assertEqual(len(tree.xpath("//table[@name='header']")), 2)
        self.assertEqual(len(tree.xpath("//table[@name='package_content']")), 1)
        self.assertEqual(len(tree.xpath("//table[@name='bulk_content']")), 1)
