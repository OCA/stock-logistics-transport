# Copyright 2021 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    shipment_advice_outgoing_backorder_policy = fields.Selection(
        string="Shipment Advice: Outgoing backorder policy",
        selection=[
            ("create_backorder", "Create backorder"),
            ("leave_open", "Leave open"),
        ],
        default="create_backorder",
        help=(
            "If you want that closing an outgoing shipment advice marks as "
            "done all related deliveries and creates backorder in case of "
            "partial choose 'Create backorder'.\nIf you want to mark "
            "deliveries as done only when they are all loaded in a shipment "
            "advice choose 'Leave open'. This last option is useful when your "
            "deliveries will be shipped by several trucks."
        ),
    )
    shipment_advice_run_in_queue_job = fields.Boolean(
        string="Run shipment advice in queue job",
        help="To prevent timeouts for large shipments, enable this option to execute "
        "shipment advice validation through a queued jobs. Each picking will be "
        "validated in a separate job.",
    )
