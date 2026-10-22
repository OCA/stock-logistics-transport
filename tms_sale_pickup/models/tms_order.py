# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class TMSOrder(models.Model):
    _inherit = "tms.order"

    def _sum_cargo(self, amount_field, uom_field, target_uom):
        """Count a pickup instead of the sold line once a pickup exists."""
        self.ensure_one()
        cargos = self.cargo_ids.filtered(lambda cargo: not cargo.pickup_ids)
        total = 0.0
        for cargo in cargos:
            amount = cargo[amount_field]
            uom = cargo[uom_field]
            if target_uom and uom:
                total += uom._compute_quantity(amount, target_uom)
            else:
                total += amount
        return total

    def _pickup_sale_lines(self):
        lines = self.sale_line_id
        lines |= self.cargo_ids.sale_line_id
        return lines

    def _hold_volume_delivery_until_complete(self):
        completed = self.env.ref("tms.tms_stage_order_completed")
        for trip in self:
            lines = trip._pickup_sale_lines().filtered(
                lambda line: line.product_id.product_tmpl_id.transport_type
                == "cargo"
            )
            for line in lines:
                trips = line.tms_order_ids | line.cargo_ids.order_id
                if trips and any(item.stage_id != completed for item in trips):
                    line.qty_delivered = 0.0

    def write(self, vals):
        completing = self.browse()
        if vals.get("stage_id"):
            stage = self.env["tms.stage"].browse(vals["stage_id"])
            if stage.is_completed:
                completing = self
        result = super().write(vals)
        if completing:
            completing._hold_volume_delivery_until_complete()
            sales = self.env["sale.order"]
            for trip in completing:
                sales |= trip.sale_id
                sales |= trip._pickup_sale_lines().order_id
            sales._create_tms_factor_adjustment()
        return result
