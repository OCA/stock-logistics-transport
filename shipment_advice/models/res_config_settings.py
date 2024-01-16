# Copyright 2021 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    shipment_advice_outgoing_backorder_policy = fields.Selection(
        related="company_id.shipment_advice_outgoing_backorder_policy", readonly=False
    )
    shipment_advice_run_in_queue_job = fields.Boolean(
        related="company_id.shipment_advice_run_in_queue_job", readonly=False
    )
