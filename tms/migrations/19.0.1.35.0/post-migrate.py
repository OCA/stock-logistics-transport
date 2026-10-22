from odoo import SUPERUSER_ID, api, fields

# OpenStreetMap coordinates for the demo locations. The demo file is noupdate,
# so an existing database keeps those partners until this migration fills them.
_LOCATIONS = {
    "tms.demo_location_1": (19.4247897, -99.1948518),
    "tms.demo_location_2": (25.6530621, -100.2943069),
    "tms.demo_location_3": (20.5787461, -100.3490319),
    "tms.demo_location_4": (20.5959313, -100.3737996),
    "tms.demo_location_5": (20.5943526, -100.3927594),
    "tms.demo_location_6": (20.5930735, -100.4098745),
    "tms.demo_location_7": (20.5909633, -100.3934582),
    "tms.demo_location_8": (20.5930221, -100.3896405),
    "tms.demo_location_9": (29.4261578, -98.4866962),
    "tms.demo_location_10": (29.5513096, -95.0974022),
}


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    today = fields.Date.context_today(env["res.partner"])
    for xmlid, (latitude, longitude) in _LOCATIONS.items():
        partner = env.ref(xmlid, raise_if_not_found=False)
        if not partner or partner.partner_latitude or partner.partner_longitude:
            continue
        partner.write(
            {
                "partner_latitude": latitude,
                "partner_longitude": longitude,
                "date_localization": today,
            }
        )
