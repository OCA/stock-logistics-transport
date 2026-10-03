# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.depends("product_id", "tms_route_id")
    def _compute_sale_order_line_tms(self):
        super()._compute_sale_order_line_tms()
        for line in self:
            template = line.product_id.product_tmpl_id
            if template.tms_factor_type == "volume" and template.tms_factor_volume_uom:
                line.tms_factor_uom = template.tms_factor_volume_uom.name

    @api.constrains("product_uom_qty", "product_id", "has_trip_product")
    def _check_volume_trip_quantity(self):
        for line in self:
            template = line.product_id.product_tmpl_id
            if (
                line.has_trip_product
                and template.tms_factor_type == "volume"
                and line.product_uom_qty != 1
            ):
                raise ValidationError(
                    self.env._(
                        "A volume service is one shipment. Keep the quantity at "
                        "1 and enter the volume on the cargo lines."
                    )
                )

    def _sync_tms_volume_factor_from_cargo(self):
        for line in self:
            template = line.product_id.product_tmpl_id
            target = template.tms_factor_volume_uom
            parents = line.cargo_ids.filtered(lambda cargo: not cargo.parent_id)
            if (
                template.tms_factor_type != "volume"
                or not target
                or not parents
                or line.qty_invoiced
            ):
                continue
            line.tms_factor = line._tms_sum_measure(
                parents, "volume", "volume_uom_id", target
            )

    def _tms_sum_measure(self, cargos, amount_field, uom_field, target):
        total = 0.0
        for cargo in cargos:
            amount = cargo[amount_field]
            uom = cargo[uom_field]
            if target and uom:
                total += uom._compute_quantity(amount, target)
            else:
                total += amount
        return total

    def _tms_actual_measure(self, amount_field, uom_field, target):
        self.ensure_one()
        parents = self.cargo_ids.filtered(lambda cargo: not cargo.parent_id)
        if not parents:
            return None
        rows = self.env["tms.cargo"]
        for parent in parents:
            rows |= parent.pickup_ids or parent
        return self._tms_sum_measure(rows, amount_field, uom_field, target)

    def _tms_odometer_uom(self):
        return self.env["res.config.settings"]._configured_uom(
            "tms.default_distance_uom", "uom.product_uom_km"
        )

    def _tms_driven_distance(self, trips):
        """Return the odometer difference, or None when a reading is missing."""
        self.ensure_one()
        driven = 0.0
        for trip in trips:
            if not trip.odometer_start_id or not trip.odometer_end_id:
                return None
            driven += trip.odometer_end - trip.odometer_start
        source = self._tms_odometer_uom()
        target = self.product_id.product_tmpl_id.tms_factor_distance_uom
        if source and target:
            return source._compute_quantity(driven, target)
        return driven

    def _tms_billable_factor(self):
        """Factor to bill once every trip of this line is completed."""
        self.ensure_one()
        template = self.product_id.product_tmpl_id
        kind = template.tms_factor_type
        if kind == "weight":
            value = self._tms_actual_measure(
                "weight", "weight_uom_id", template.tms_factor_weight_uom
            )
        elif kind == "volume":
            value = self._tms_actual_measure(
                "volume", "volume_uom_id", template.tms_factor_volume_uom
            )
        elif kind == "distance":
            trips = self.tms_order_ids | self.cargo_ids.order_id
            value = self._tms_driven_distance(trips)
        else:
            value = None
        if value is None:
            return self.tms_factor
        return value

    def _tms_invoiced_factor(self):
        self.ensure_one()
        total = 0.0
        for invoice_line in self.invoice_lines:
            move = invoice_line.move_id
            if move.state == "cancel" or move.move_type not in (
                "out_invoice",
                "out_refund",
            ):
                continue
            sign = -1.0 if move.move_type == "out_refund" else 1.0
            total += sign * (invoice_line.tms_factor or 0.0)
        return total

    def _tms_factor_delta(self):
        self.ensure_one()
        return self.tms_factor - self._tms_invoiced_factor()

    def _tms_needs_factor_adjustment(self):
        self.ensure_one()
        return bool(self.tms_factor_type) and float_compare(
            self._tms_factor_delta(), 0.0, precision_rounding=0.01
        )
