# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import odoo.tests


def hoot_error_checker(message):
    """Allow HOOT framework messages through, stop on other errors."""
    return "[HOOT]" not in message


@odoo.tests.tagged("post_install", "-at_install")
class TestTmsDeliveryStopsLeafletJS(odoo.tests.HttpCase):
    def test_js_unit(self):
        self.browser_js(
            "/web/tests?headless&loglevel=2&preset=desktop"
            "&timeout=30000"
            "&filter=tms_stops_map_scenarios",
            "",
            "",
            login="admin",
            timeout=600,
            success_signal="[HOOT] Test suite succeeded",
            error_checker=hoot_error_checker,
        )
