from odoo import fields, models


class TMSStage(models.Model):
    _inherit = "tms.stage"

    stop_state_sync = fields.Selection(
        [
            ("draft", "Draft"),
            ("scheduled", "Scheduled"),
            ("delivered", "Delivered"),
            ("skipped", "Skipped"),
        ],
        help="When an order is in this stage, sync all its stops "
        "to this state. Leave empty to not enforce state sync.",
    )
