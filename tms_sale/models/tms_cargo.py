# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class TMSCargo(models.Model):
    _inherit = "tms.cargo"

    sale_line_id = fields.Many2one("sale.order.line", copy=False, ondelete="set null")

    def _link_sale_line_from_trip(self):
        """Copy the trip sale line only while that trip carries one sale."""
        for cargo in self:
            if cargo.sale_line_id or not cargo.order_id:
                continue
            trip = cargo.order_id
            sale_lines = (trip.cargo_ids - cargo).sale_line_id
            if trip.sale_line_id:
                sale_lines |= trip.sale_line_id
            if len(sale_lines) != 1:
                continue
            cargo.with_context(skip_cargo_sale_sync=True).sale_line_id = sale_lines

    def _link_trip_from_sale_line(self):
        for cargo in self:
            trips = cargo.sale_line_id.tms_order_ids
            if cargo.sale_line_id and not cargo.order_id and len(trips) == 1:
                cargo.with_context(skip_cargo_sale_sync=True).order_id = trips.id

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if self.env.context.get("skip_cargo_sale_sync"):
            return records
        records._link_sale_line_from_trip()
        records._link_trip_from_sale_line()
        records.sale_line_id._sync_tms_weight_factor_from_cargo()
        return records

    def write(self, vals):
        result = super().write(vals)
        if self.env.context.get("skip_cargo_sale_sync"):
            return result
        if "order_id" in vals:
            self._link_sale_line_from_trip()
        if "sale_line_id" in vals:
            self._link_trip_from_sale_line()
        tracked = {"weight", "weight_uom_id", "sale_line_id", "order_id"}
        if tracked & set(vals):
            self.sale_line_id._sync_tms_weight_factor_from_cargo()
        return result

    def unlink(self):
        lines = self.sale_line_id
        result = super().unlink()
        lines._sync_tms_weight_factor_from_cargo()
        return result
