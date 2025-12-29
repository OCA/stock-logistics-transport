# Copyright 2026 Binhex
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import re

from .common import Common


class TestShipmentAdviceMail(Common):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.template = cls.env.ref("shipment_advice.email_template_shipment_advice")
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Shipment Advice Customer",
                "street": "Calle Mayor 1",
                "city": "Madrid",
                "country_id": cls.env.ref("base.es").id,
            }
        )

    def _create_unreserved_picking(self):
        product = self.env["product.product"].create(
            {"name": "Unreserved product", "type": "product", "weight": 1.0}
        )
        location = self.picking_type_out.default_location_src_id
        location_dest = self.picking_type_out.default_location_dest_id
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.picking_type_out.id,
                "location_id": location.id,
                "location_dest_id": location_dest.id,
                "partner_id": self.partner.id,
                "origin": "SO-UNRESERVED",
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "name": product.display_name,
                            "product_id": product.id,
                            "product_uom_qty": 2,
                            "product_uom": product.uom_id.id,
                            "location_id": location.id,
                            "location_dest_id": location_dest.id,
                        },
                    )
                ],
            }
        )
        picking.action_confirm()
        picking.do_unreserve()
        return picking

    def _render(self, advice, field):
        return self.template._render_field(field, [advice.id])[advice.id]

    def _prepare_advice_with_picking(self, advice, picking, origin):
        picking.write({"origin": origin, "partner_id": self.partner.id})
        self.plan_records_in_shipment(advice, picking)
        self.progress_shipment_advice(advice, dock=self.dock)

    def test_get_mail_template(self):
        self.assertEqual(
            self.shipment_advice_out._get_mail_template(),
            "shipment_advice.email_template_shipment_advice",
        )

    def test_action_send_email(self):
        action = self.shipment_advice_out.action_send_email()
        self.assertEqual(action["res_model"], "mail.compose.message")
        self.assertEqual(action["target"], "new")
        ctx = action["context"]
        self.assertEqual(ctx["default_model"], "shipment.advice")
        self.assertEqual(ctx["default_res_id"], self.shipment_advice_out.id)
        self.assertEqual(ctx["default_template_id"], self.template.id)
        self.assertTrue(ctx["default_use_template"])
        self.assertEqual(ctx["default_composition_mode"], "comment")
        self.assertTrue(ctx["force_email"])

    def test_email_body_in_progress_with_dock(self):
        advice = self.shipment_advice_out
        picking = self.move_product_out1.picking_id
        self._prepare_advice_with_picking(advice, picking, "SO-EMAIL-01")
        body = self._render(advice, "body_html")
        self.assertIn("from %s" % self.dock.name, body)
        self.assertIn("SO-EMAIL-01", body)
        self.assertIn("Calle Mayor 1", body)
        # Three different products on the picking: the template shows the count
        self.assertIn(">3<", re.sub(r"\s+", "", body))
        self.assertIn(advice.name, self._render(advice, "subject"))
        self.assertEqual(
            self._render(advice, "report_name"), advice.name.replace("/", "_")
        )

    def test_email_body_confirmed_without_dock(self):
        advice = self.shipment_advice_out
        self.confirm_shipment_advice(advice)
        body = self._render(advice, "body_html")
        self.assertTrue(body.strip())
        self.assertNotIn("from %s" % self.dock.name, body)
        self.assertIn(advice.name, self._render(advice, "subject"))

    def test_email_body_unreserved_picking(self):
        advice = self.shipment_advice_out
        picking = self._create_unreserved_picking()
        self.assertFalse(picking.move_line_ids)
        self.plan_records_in_shipment(advice, picking)
        body = self._render(advice, "body_html")
        self.assertIn("Unreserved product", body)

    def test_email_attachment(self):
        advice = self.shipment_advice_out
        picking = self.move_product_out1.picking_id
        self._prepare_advice_with_picking(advice, picking, "SO-EMAIL-02")
        mail_values = self.template.generate_email(advice.id, ["subject", "body_html"])
        attachments = mail_values.get("attachments") or []
        self.assertEqual(len(attachments), 1)
        # In test mode the report is rendered as HTML: only the sanitized
        # basename and the fact that content was generated are asserted.
        attachment_name, attachment_content = attachments[0]
        self.assertEqual(
            attachment_name.rsplit(".", 1)[0], advice.name.replace("/", "_")
        )
        self.assertTrue(attachment_content)
