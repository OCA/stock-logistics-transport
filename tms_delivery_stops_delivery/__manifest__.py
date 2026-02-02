# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "TMS Delivery Stops - Delivery Integration",
    "version": "18.0.1.0.0",
    "category": "Inventory/Transport",
    "summary": "Integrate delivery carriers with TMS delivery stops",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/stock-logistics-transport",
    "license": "AGPL-3",
    "depends": [
        "delivery",
        "sale_stock",
        "stock_delivery",
        "tms",
        "tms_delivery_stops",
        "base_geolocalize",
        "stock_picking_volume",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/delivery_carrier_views.xml",
        "views/stock_picking_views.xml",
        "views/tms_order_stop_views.xml",
        "wizard/create_tms_order_wizard_views.xml",
    ],
    "demo": [
        "data/demo.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
