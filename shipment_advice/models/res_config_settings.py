# Copyright 2021 Camptocamp SA
# Copyright 2024 Michael Tietz (MT Software) <mtietz@mt-software.de>
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
    shipment_advice_auto_close_incoming = fields.Boolean(
        related="company_id.shipment_advice_auto_close_incoming", readonly=False
    )
