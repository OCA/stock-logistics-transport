# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Flag the fuel product on databases created before distance spreading."""
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    fuel = env.ref("tms_expense.expense_trip_fuel", raise_if_not_found=False)
    if fuel:
        fuel.tms_spread_by_distance = True
