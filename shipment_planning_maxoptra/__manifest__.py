# Copyright 2022 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
{
    "name": "Shipment Planning MaxOptra",
    "summary": "Plan batch pickings using MaxOptra.",
    "version": "14.0.1.0.0",
    "development_status": "Alpha",
    "author": "Camptocamp, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/stock-logistics-transport",
    "category": "Warehouse Management",
    "depends": [
        "shipment_planning",
        "stock_picking_batch",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/res_partner.xml",
        "views/shipment_planning.xml",
        "views/shipment_vehicle.xml",
        "views/stock_picking.xml",
        "views/stock_picking_batch.xml",
        "views/stock_warehouse.xml",
        "wizard/shipment_maxoptra_schedule_import.xml",
    ],
    "demo": [
        "demo/stock_warehouse.xml",
        "demo/shipment_vehicle.xml",
    ],
    "license": "AGPL-3",
    "installable": True,
    "application": False,
}
