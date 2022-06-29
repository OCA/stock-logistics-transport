# Copyright 2021 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import fields, models


class StockDock(models.Model):
    _name = "stock.dock"
    _description = "Dock, used by trucks to load/unload goods"

    name = fields.Char(required=True)
    barcode = fields.Char()
    active = fields.Boolean(default=True)
    warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse",
        ondelete="cascade",
        string="Warehouse",
        required=True,
        check_company=True,
        default=lambda self: self._default_warehouse_id(),
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        related="warehouse_id.company_id",
        readonly=True,
        store=True,
        index=True,
    )

    def _default_warehouse_id(self):
        wh = self.env.ref("stock.warehouse0", raise_if_not_found=False)
        return wh.id or False
