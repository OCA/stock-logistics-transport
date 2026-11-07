# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models

TMS_MAP_VIEW = ("tms_map", "Map")


class IrUiView(models.Model):
    _inherit = "ir.ui.view"

    type = fields.Selection(selection_add=[TMS_MAP_VIEW])

    def _is_qweb_based_view(self, view_type):
        return view_type == TMS_MAP_VIEW[0] or super()._is_qweb_based_view(view_type)

    def _get_view_info(self):
        return {"tms_map": {"icon": "fa fa-map-marker"}} | super()._get_view_info()
