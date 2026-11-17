from odoo import SUPERUSER_ID, api

_MODE_GROUPS = (
    "tms.group_tms_road_user",
    "tms.group_tms_air_user",
    "tms.group_tms_water_user",
    "tms.group_tms_rail_user",
)


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    internal = env.ref("base.group_user")
    missing = env["res.groups"]
    for xmlid in _MODE_GROUPS:
        group = env.ref(xmlid)
        if group not in internal.implied_ids:
            missing |= group
    if missing:
        internal.write({"implied_ids": [(4, group.id) for group in missing]})
