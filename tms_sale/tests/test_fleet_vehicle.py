# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.base.tests.common import BaseCommon


class TestFleetVehicleTmsSale(BaseCommon):
    def test_vehicle_form_has_no_tms_service_or_payload(self):
        fields = self.env["fleet.vehicle"]._fields
        self.assertNotIn("tms_service_product_id", fields)
        self.assertNotIn("weight_capacity", fields)
        self.assertNotIn("capacity", fields)
        self.assertNotIn("cargo_uom_id", fields)
        arch = self.env["fleet.vehicle"].get_view(view_type="form")["arch"]
        self.assertNotIn("tms_service_product_id", arch)
        self.assertNotIn('name="weight_capacity"', arch)
        self.assertNotIn('name="cargo_uom_id"', arch)
