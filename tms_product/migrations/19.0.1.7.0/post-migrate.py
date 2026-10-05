from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    product = env.ref("tms_product.product_tms_seat_service", raise_if_not_found=False)
    if product and product.name == "TMS Passenger Service":
        product.name = "TMS Seat Service"
