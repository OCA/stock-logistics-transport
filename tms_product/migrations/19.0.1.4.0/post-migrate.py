from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    names = {
        "tms_product.product_tms_air_service": "TMS Air Charter Service",
        "tms_product.product_tms_ocean_service": "TMS Vessel Chartering Service",
    }
    for xmlid, name in names.items():
        product = env.ref(xmlid, raise_if_not_found=False)
        if product and product.name != name:
            product.name = name
