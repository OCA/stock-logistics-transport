# Copyright 2025 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from odoo.exceptions import UserError
from odoo.tools import mute_logger

from odoo.addons.printing_auto_base.tests.common import (
    TestPrintingAutoCommon,
    patch_print_document,
)


@patch_print_document()
class TestAutoPrinting(TestPrintingAutoCommon):
    @classmethod
    def setUpReportAndRecord(cls):
        cls.report_ref = "shipment_advice.action_report_shipment_advice"
        cls.record = cls.env["shipment.advice"].create({"shipment_type": "outgoing"})

    def setUp(self):
        # Note: Using setUpClass, cls.record.auto_printing_ids
        # is reset on each test making them fail
        super().setUp()
        self.printing_auto = self._create_printing_auto_attachment()
        self._create_attachment(self.record, self.data, "1")
        self.record.warehouse_id.shipment_advice_auto_printing_ids |= self.printing_auto

    def test_action_done_printing_auto(self):
        self.printing_auto.printer_id = self.printer_1
        self.record._action_done()
        self.assertFalse(self.record.printing_auto_error)

    def test_action_done_printing_error_log(self):
        with mute_logger("odoo.addons.printing_auto_base.models.printing_auto_mixin"):
            self.record._action_done()
        self.assertTrue(self.record.printing_auto_error)

    def test_action_done_printing_error_raise(self):
        self.printing_auto.action_on_error = "raise"
        msg = "^No printer configured to print this Printing auto attachment.$"
        with self.assertRaisesRegex(UserError, msg):
            self.record._action_done()
