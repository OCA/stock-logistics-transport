from datetime import date, timedelta

from odoo import fields
from odoo.tests.common import TransactionCase


class TestTmsDocument(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.holder = cls.env["tms.driver"].create({"name": "Doc Holder"})
        cls.Doc = cls.env["tms.document"]

    def _doc(self, expiry):
        return self.Doc.create({
            "res_model": "tms.driver",
            "res_id": self.holder.id,
            "doc_type": "license",
            "name": "LIC-1",
            "expiry_date": expiry,
        })

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
