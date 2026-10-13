from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    modes = {
        "tms_product.product_tms_trip_service": "ftl",
        "tms_product.product_tms_cargo_service": "ltl",
    }
    names = {
        "tms_product.product_tms_trip_service": "TMS FTL Service",
        "tms_product.product_tms_cargo_service": "TMS LTL Service",
        "tms_product.product_tms_seat_service": "TMS Passenger Service",
    }
    for xmlid, name in names.items():
        product = env.ref(xmlid, raise_if_not_found=False)
        if not product:
            continue
        mode = modes.get(xmlid)
        if mode and product.transport_type == "cargo" and not product.cargo_mode:
            product.cargo_mode = mode
        if product.name != name:
            product.name = name
