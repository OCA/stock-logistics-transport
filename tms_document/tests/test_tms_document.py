import base64
from datetime import date, timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.service.model import call_kw
from odoo.tests.common import TransactionCase


class TestTmsDocument(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.holder = cls.env["tms.driver"].create({"name": "Doc Holder"})
        cls.Doc = cls.env["tms.document"]
        # Disable core inline insurance/license checks to isolate our guard.
        ICP = cls.env["ir.config_parameter"].sudo()
        ICP.set_param("tms.default_vehicle_insurance_security_days", "0")
        ICP.set_param("tms.default_driver_license_security_days", "0")
        cls.order = cls.env["tms.order"].create({"driver_id": cls.holder.id})

    def _doc(self, expiry):
        return self.Doc.create(
            {
                "res_model": "tms.driver",
                "res_id": self.holder.id,
                "doc_type": "license",
                "name": "LIC-1",
                "expiry_date": expiry,
            }
        )

    def _make_vehicle(self):
        brand = self.env["fleet.vehicle.model.brand"].create({"name": "Test Brand"})
        model = self.env["fleet.vehicle.model"].create(
            {"name": "Test Model", "brand_id": brand.id}
        )
        return self.env["fleet.vehicle"].create({"model_id": model.id})

    def test_state_valid(self):
        d = self._doc(fields.Date.to_date(date.today()) + timedelta(days=400))
        self.assertEqual(d.state, "valid")

    def test_state_expired(self):
        d = self._doc(fields.Date.to_date(date.today()) - timedelta(days=1))
        self.assertEqual(d.state, "expired")

    def test_state_expiring_within_horizon(self):
        d = self._doc(fields.Date.to_date(date.today()) + timedelta(days=5))
        self.assertEqual(d.state, "expiring")

    def test_horizon_respected(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "tms.document.expiry_horizon_days", 60
        )
        d = self._doc(fields.Date.to_date(date.today()) + timedelta(days=40))
        self.assertEqual(d.state, "expiring")  # within 60-day horizon

    def test_driver_documents_o2m(self):
        self._doc(fields.Date.to_date(date.today()) + timedelta(days=400))
        self.assertEqual(len(self.holder.document_ids), 1)
        self.assertEqual(self.holder.document_ids.state, "valid")

    def test_start_blocked_when_critical_expired(self):
        doc = self._doc(fields.Date.to_date(date.today()) - timedelta(days=1))
        doc.critical = True
        with self.assertRaises(UserError):
            self.order.button_start_order()

    def test_start_ok_when_no_critical_expired(self):
        doc = self._doc(fields.Date.to_date(date.today()) + timedelta(days=400))
        doc.critical = True
        self.order.button_start_order()
        self.assertTrue(self.order.start_trip)

    def test_start_blocked_when_vehicle_critical_expired(self):
        vehicle = self._make_vehicle()
        doc = self.Doc.create(
            {
                "res_model": "fleet.vehicle",
                "res_id": vehicle.id,
                "doc_type": "insurance",
                "name": "INS-1",
                "expiry_date": fields.Date.to_date(date.today()) - timedelta(days=1),
            }
        )
        doc.critical = True
        order = self.env["tms.order"].create({"vehicle_id": vehicle.id})
        with self.assertRaises(UserError):
            order.button_start_order()

    def test_start_ok_when_expired_but_not_critical(self):
        doc = self._doc(fields.Date.to_date(date.today()) - timedelta(days=1))
        doc.critical = False
        self.order.button_start_order()
        self.assertTrue(self.order.start_trip)

    def test_start_ok_when_critical_expiring(self):
        doc = self._doc(fields.Date.to_date(date.today()) + timedelta(days=5))
        doc.critical = True
        self.order.button_start_order()
        self.assertTrue(self.order.start_trip)

    def test_state_expiring_on_today_boundary(self):
        d = self._doc(fields.Date.to_date(date.today()))
        self.assertEqual(d.state, "expiring")

    def test_res_ref_points_to_holder(self):
        d = self._doc(fields.Date.to_date(date.today()) + timedelta(days=400))
        self.assertEqual(d.res_ref, self.holder)

    def test_create_document_from_attachment(self):
        attachment = self.env["ir.attachment"].create(
            {"name": "license.pdf", "datas": base64.b64encode(b"file-content")}
        )
        result = self.Doc.with_context(
            default_res_model="tms.driver", default_res_id=self.holder.id
        ).create_document_from_attachment(attachment.ids)
        self.assertEqual(result["count"], 1)
        docs = self.Doc.browse(result["ids"])
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs.name, "license.pdf")
        self.assertEqual(docs.file_id, attachment)
        self.assertEqual(attachment.res_model, "tms.driver")
        self.assertEqual(attachment.res_id, self.holder.id)

    def test_create_document_from_attachment_requires_holder(self):
        attachment = self.env["ir.attachment"].create(
            {"name": "license.pdf", "datas": base64.b64encode(b"file-content")}
        )
        with self.assertRaises(UserError):
            self.Doc.create_document_from_attachment(attachment.ids)

    def test_create_document_from_attachment_with_holder(self):
        attachment = self.env["ir.attachment"].create(
            {"name": "insurance.pdf", "datas": base64.b64encode(b"file-content")}
        )
        result = self.Doc.with_context(
            default_res_model="tms.driver", default_res_id=self.holder.id
        ).create_document_from_attachment(attachment.ids)
        docs = self.Doc.browse(result["ids"])
        self.assertEqual(docs.res_model, "tms.driver")
        self.assertEqual(docs.res_id, self.holder.id)

    def test_create_document_from_attachment_via_rpc(self):
        """The web client sends args=[attachment_ids] which call_kw treats as
        record ids (args[0]) unless the method is marked @api.model."""
        attachment = self.env["ir.attachment"].create(
            {"name": "via-rpc.pdf", "datas": base64.b64encode(b"file-content")}
        )
        result = call_kw(
            self.Doc,
            "create_document_from_attachment",
            [[attachment.id]],
            {
                "context": {
                    "default_res_model": "tms.driver",
                    "default_res_id": self.holder.id,
                }
            },
        )
        self.assertEqual(result["count"], 1)
        docs = self.Doc.browse(result["ids"])
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs.name, "via-rpc.pdf")
        self.assertEqual(docs.res_model, "tms.driver")
        self.assertEqual(docs.res_id, self.holder.id)

    def test_unlink_soft_deletes_document(self):
        doc = self._doc(fields.Date.to_date(date.today()) - timedelta(days=1))
        doc.critical = True
        doc.unlink()
        self.assertFalse(doc.active)
        self.assertNotIn(doc, self.holder.document_ids)

    def test_action_soft_delete_archives_and_unblocks_start(self):
        doc = self._doc(fields.Date.to_date(date.today()) - timedelta(days=1))
        doc.critical = True
        with self.assertRaises(UserError):
            self.order.button_start_order()
        doc.action_soft_delete()
        self.assertFalse(doc.active)
        self.assertNotIn(doc, self.holder.document_ids)
        self.order.button_start_order()
        self.assertTrue(self.order.start_trip)

    def test_driver_document_ids_editable(self):
        field = self.env["tms.driver"]._fields["document_ids"]
        self.assertFalse(field.readonly)
        self.assertTrue(field.inverse)

    def test_vehicle_document_ids_editable(self):
        field = self.env["fleet.vehicle"]._fields["document_ids"]
        self.assertFalse(field.readonly)
        self.assertTrue(field.inverse)

    def test_create_document_via_driver_document_ids(self):
        self.holder.document_ids = [
            (
                0,
                0,
                {
                    "res_model": "tms.driver",
                    "doc_type": "license",
                    "name": "LIC-NEW",
                    "expiry_date": fields.Date.to_date(date.today())
                    + timedelta(days=400),
                },
            )
        ]
        self.assertEqual(len(self.holder.document_ids), 1)
        new_doc = self.holder.document_ids
        self.assertEqual(new_doc.name, "LIC-NEW")
        self.assertEqual(new_doc.res_model, "tms.driver")
        self.assertEqual(new_doc.res_id, self.holder.id)

    def test_edit_document_fields_via_document_ids(self):
        doc = self._doc(fields.Date.to_date(date.today()) + timedelta(days=400))
        self.holder.document_ids.write(
            {"critical": True, "expiry_date": fields.Date.to_date(date.today())}
        )
        self.assertTrue(doc.critical)
        self.assertEqual(doc.expiry_date, fields.Date.to_date(date.today()))

    def test_create_logs_message_in_chatter(self):
        d = self._doc(fields.Date.to_date(date.today()) + timedelta(days=400))
        self.assertTrue(d.message_ids)

    def test_update_tracked_field_logs_message(self):
        d = self._doc(fields.Date.to_date(date.today()) + timedelta(days=400))
        self.env.cr.precommit.run()
        before = d.message_ids
        d.write({"critical": True})
        self.env.cr.precommit.run()
        new_messages = d.message_ids - before
        self.assertTrue(new_messages)
        tracked_fields = new_messages.tracking_value_ids.field_id.name
        self.assertIn("critical", tracked_fields)

    def test_update_expiry_logs_message(self):
        d = self._doc(fields.Date.to_date(date.today()) + timedelta(days=400))
        self.env.cr.precommit.run()
        before = d.message_ids
        new_expiry = fields.Date.to_date(date.today()) + timedelta(days=50)
        d.write({"expiry_date": new_expiry})
        self.env.cr.precommit.run()
        new_messages = d.message_ids - before
        self.assertTrue(new_messages)
        tracked_fields = new_messages.tracking_value_ids.field_id.name
        self.assertIn("expiry_date", tracked_fields)

    def test_cannot_delete_document_file_attachment(self):
        attachment = self.env["ir.attachment"].create(
            {"name": "doc-file.pdf", "datas": base64.b64encode(b"file-content")}
        )
        self.Doc.with_context(
            default_res_model="tms.driver", default_res_id=self.holder.id
        ).create_document_from_attachment(attachment.ids)
        self.assertTrue(attachment.exists())
        with self.assertRaises(UserError):
            attachment.unlink()
        self.assertTrue(attachment.exists())

    def test_cannot_delete_legacy_document_attachment(self):
        doc = self._doc(fields.Date.to_date(date.today()) + timedelta(days=400))
        file_att = self.env["ir.attachment"].create(
            {
                "name": "legacy.pdf",
                "res_model": "tms.document",
                "res_id": doc.id,
                "datas": base64.b64encode(b"file-content"),
            }
        )
        with self.assertRaises(UserError):
            file_att.unlink()
        self.assertTrue(file_att.exists())

    def test_can_delete_attachment_not_linked_to_document(self):
        att = self.env["ir.attachment"].create(
            {"name": "junk.txt", "datas": base64.b64encode(b"x")}
        )
        att.unlink()
        self.assertFalse(att.exists())

    def test_create_document_keeps_source_attachment_on_holder(self):
        attachment = self.env["ir.attachment"].create(
            {"name": "license.pdf", "datas": base64.b64encode(b"file-content")}
        )
        self.Doc.with_context(
            default_res_model="tms.driver", default_res_id=self.holder.id
        ).create_document_from_attachment(attachment.ids)
        self.assertTrue(attachment.exists())
        self.assertEqual(attachment.res_model, "tms.driver")
        self.assertEqual(attachment.res_id, self.holder.id)

    def test_soft_delete_removes_document_file_from_attachments(self):
        attachment = self.env["ir.attachment"].create(
            {"name": "license.pdf", "datas": base64.b64encode(b"file-content")}
        )
        result = self.Doc.with_context(
            default_res_model="tms.driver", default_res_id=self.holder.id
        ).create_document_from_attachment(attachment.ids)
        doc = self.Doc.browse(result["ids"])
        doc.action_soft_delete()
        self.assertFalse(doc.active)
        self.assertFalse(doc.file_id)
        self.assertFalse(attachment.exists())

    def test_action_replace_file(self):
        doc = self._doc(fields.Date.to_date(date.today()) + timedelta(days=400))
        old_file = self.env["ir.attachment"].create(
            {"name": "old.pdf", "datas": base64.b64encode(b"old")}
        )
        doc.file_id = old_file
        new_file = self.env["ir.attachment"].create(
            {"name": "new.pdf", "datas": base64.b64encode(b"new")}
        )
        result = doc.action_replace_file(new_file.id)
        self.assertTrue(result)
        self.assertEqual(doc.file_id, new_file)
        self.assertFalse(old_file.exists())
        self.assertEqual(new_file.res_model, "tms.driver")
        self.assertEqual(new_file.res_id, self.holder.id)

    def test_action_replace_file_without_old_file(self):
        doc = self._doc(fields.Date.to_date(date.today()) + timedelta(days=400))
        self.assertFalse(doc.file_id)
        new_file = self.env["ir.attachment"].create(
            {"name": "fresh.pdf", "datas": base64.b64encode(b"fresh")}
        )
        doc.action_replace_file(new_file.id)
        self.assertEqual(doc.file_id, new_file)
        self.assertTrue(new_file.exists())

    def test_action_replace_file_missing_attachment(self):
        doc = self._doc(fields.Date.to_date(date.today()) + timedelta(days=400))
        with self.assertRaises(UserError):
            doc.action_replace_file(0)

    def test_create_document_from_attachment_no_attachment(self):
        with self.assertRaises(UserError):
            self.Doc.with_context(
                default_res_model="tms.driver", default_res_id=self.holder.id
            ).create_document_from_attachment([])

    def test_move_document_to_other_holder_via_inverse(self):
        doc = self._doc(fields.Date.to_date(date.today()) + timedelta(days=400))
        vehicle = self._make_vehicle()
        vehicle.document_ids = doc
        self.assertEqual(doc.res_model, "fleet.vehicle")
        self.assertEqual(doc.res_id, vehicle.id)
        self.assertEqual(len(vehicle.document_ids), 1)

    def test_vehicle_unlink_archives_documents(self):
        vehicle = self._make_vehicle()
        doc = self.Doc.create(
            {
                "res_model": "fleet.vehicle",
                "res_id": vehicle.id,
                "doc_type": "inspection",
                "name": "VEH-INSP",
            }
        )
        vehicle.unlink()
        self.assertFalse(doc.active)
