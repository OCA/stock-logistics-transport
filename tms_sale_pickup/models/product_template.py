# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    tms_factor_type = fields.Selection(
        selection_add=[("volume", "Volume")],
        ondelete={"volume": "set default"},
    )
    tms_factor_volume_uom = fields.Many2one(
        "uom.uom",
        domain=lambda self: self.env["res.config.settings"]._volume_domain(),
        string="Volume Unit of Measure",
        compute="_compute_restore_transport_line_fields",
        store=True,
        readonly=False,
    )

    @api.depends("tms_trip")
    def _compute_restore_transport_line_fields(self):
        result = super()._compute_restore_transport_line_fields()
        for product in self:
            if not product.tms_trip:
                product.tms_factor_volume_uom = False
        return result
