from datetime import date, timedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase


class TestSecurity(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.driver = cls.env["tms.driver"].create({"name": "Sec Driver"})
        cls.Doc = cls.env["tms.document"]
        cls.doc = cls.Doc.create(
            {
                "res_model": "tms.driver",
                "res_id": cls.driver.id,
                "doc_type": "license",
                "name": "SEC-LIC",
                "expiry_date": fields.Date.to_date(date.today()) + timedelta(days=365),
            }
        )

        cls.tms_user = cls.env["res.users"].create(
            {
                "name": "TMS User",
                "login": "tms_user_sec",
                "group_ids": [(6, 0, [cls.env.ref("tms.group_tms_user").id])],
            }
        )
        cls.tms_admin = cls.env["res.users"].create(
            {
                "name": "TMS Admin",
                "login": "tms_admin_sec",
                "group_ids": [(6, 0, [cls.env.ref("tms.group_tms_admin").id])],
            }
        )

    def test_group_exists(self):
        self.env.ref("tms_document.group_tms_document", raise_if_not_found=True)

    def test_group_implied_by_admin(self):
        """tms_admin should have CRUD access via implied group_tms_document."""
        new_doc = self.Doc.with_user(self.tms_admin).create(
            {
                "res_model": "tms.driver",
                "res_id": self.driver.id,
                "doc_type": "insurance",
                "name": "ADMIN-CHECK",
            }
        )
        self.assertTrue(new_doc.id)
        new_doc.with_user(self.tms_admin).write({"name": "ADMIN-RENAMED"})
        self.assertEqual(new_doc.name, "ADMIN-RENAMED")

    def test_user_read_allowed(self):
        """tms_user can read documents."""
        docs = self.Doc.with_user(self.tms_user).search([("id", "=", self.doc.id)])
        self.assertIn(self.doc, docs)

    def test_user_write_denied(self):
        """tms_user without group_tms_document cannot write."""
        with self.assertRaises(AccessError):
            self.doc.with_user(self.tms_user).write({"name": "HACKED"})

    def test_user_create_denied(self):
        """tms_user without group_tms_document cannot create."""
        with self.assertRaises(AccessError):
            self.Doc.with_user(self.tms_user).create(
                {
                    "res_model": "tms.driver",
                    "res_id": self.driver.id,
                    "doc_type": "license",
                    "name": "NEW",
                }
            )

    def test_admin_crud_allowed(self):
        """tms_admin (implies group_tms_document) has full CRUD."""
        doc = self.doc.with_user(self.tms_admin)
        doc.write({"name": "RENAMED"})
        self.assertEqual(doc.name, "RENAMED")
        new_doc = self.Doc.with_user(self.tms_admin).create(
            {
                "res_model": "tms.driver",
                "res_id": self.driver.id,
                "doc_type": "insurance",
                "name": "ADMIN-INS",
            }
        )
        self.assertTrue(new_doc.id)

    def test_multi_company_isolation(self):
        """Documents are isolated by company via ir.rule."""
        company_b = self.env["res.company"].create({"name": "Company B"})
        doc_b = self.Doc.create(
            {
                "res_model": "tms.driver",
                "res_id": self.driver.id,
                "doc_type": "license",
                "name": "COMP-B-LIC",
                "company_id": company_b.id,
            }
        )
        user_b = self.env["res.users"].create(
            {
                "name": "User B",
                "login": "user_b_sec",
                "group_ids": [(6, 0, [self.env.ref("tms.group_tms_admin").id])],
                "company_ids": [(6, 0, [company_b.id])],
                "company_id": company_b.id,
            }
        )
        visible = self.Doc.with_user(user_b).search([])
        self.assertIn(doc_b, visible)
        self.assertNotIn(self.doc, visible)

    def test_res_model_constraint_rejects_invalid_model(self):
        from odoo.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            self.Doc.create(
                {
                    "res_model": "res.partner",
                    "res_id": 1,
                    "doc_type": "other",
                    "name": "BAD",
                }
            )

    def test_res_ref_writable(self):
        """res_ref can be set directly via inverse."""
        vehicle_brand = self.env["fleet.vehicle.model.brand"].create({"name": "Brand"})
        vehicle_model = self.env["fleet.vehicle.model"].create(
            {"name": "Model", "brand_id": vehicle_brand.id}
        )
        vehicle = self.env["fleet.vehicle"].create({"model_id": vehicle_model.id})
        doc = self.Doc.create(
            {
                "doc_type": "insurance",
                "name": "VIA-REF",
                "res_model": "tms.driver",
                "res_id": self.driver.id,
            }
        )
        doc.res_ref = f"fleet.vehicle,{vehicle.id}"
        self.assertEqual(doc.res_model, "fleet.vehicle")
        self.assertEqual(doc.res_id, vehicle.id)

    def test_res_ref_clearable(self):
        """Clearing res_ref via inverse clears the raw fields."""
        doc = self.Doc.create(
            {
                "doc_type": "insurance",
                "name": "VIA-CLEAR",
                "res_model": "tms.driver",
                "res_id": self.driver.id,
            }
        )
        doc.res_ref = False
        self.assertFalse(doc.res_model)
        self.assertFalse(doc.res_id)

    def test_critical_check_uses_sudo(self):
        """Critical check via sudo sees documents even if user lacks
        read access to tms.document (safety check)."""
        self.Doc.create(
            {
                "res_model": "tms.driver",
                "res_id": self.driver.id,
                "doc_type": "license",
                "name": "CRIT-LIC",
                "expiry_date": fields.Date.to_date(date.today()) - timedelta(days=1),
                "critical": True,
            }
        )
        order = self.env["tms.order"].create({"driver_id": self.driver.id})
        with self.assertRaises(UserError):
            order.with_user(self.tms_user).button_start_order()

    def test_cascade_archive_on_driver_unlink(self):
        """Deleting a driver archives its documents."""
        driver = self.env["tms.driver"].create({"name": "Doomed"})
        doc = self.Doc.create(
            {
                "res_model": "tms.driver",
                "res_id": driver.id,
                "doc_type": "license",
                "name": "CASC-LIC",
            }
        )
        driver.unlink()
        self.assertFalse(doc.active)
