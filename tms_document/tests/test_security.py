from odoo.tests.common import TransactionCase


class TestSecurity(TransactionCase):
    def test_group_exists(self):
        self.env.ref("tms_document.group_tms_document", raise_if_not_found=True)
