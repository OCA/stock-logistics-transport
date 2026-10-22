# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models
from odoo.tools.float_utils import float_compare


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def write(self, vals):
        result = super().write(vals)
        if vals.get("state") == "sale":
            cargos = self.order_line.cargo_ids.filtered(
                lambda cargo: not cargo.parent_id and not cargo.sold_locked
            )
            cargos.write({"sold_locked": True})
        return result

    def _tms_expected_trip_count(self, line):
        template = line.product_id.product_tmpl_id
        if line.has_trip_product and template.tms_factor_type == "volume":
            return 1 if line.product_uom_qty else 0
        return super()._tms_expected_trip_count(line)

    def remove_lines_with_trips(
        self, initial_trips, initial_line_ids, initial_quantities
    ):
        current_order_line_ids = set(self.order_line.ids)
        removed_lines = initial_line_ids - current_order_line_ids
        if removed_lines:
            trips_to_delete = initial_trips.filtered(
                lambda trip: not (trip.sale_line_id & self.order_line)
            )
            if trips_to_delete:
                trips_to_delete.unlink()
        kept_factors = ("weight", "volume")
        for line in self.order_line:
            if line.id not in initial_quantities:
                continue
            if line.product_id.product_tmpl_id.tms_factor_type in kept_factors:
                continue
            if line.product_uom_qty < initial_quantities[line.id]:
                trips_to_delete = line.tms_order_ids[:1]
                if trips_to_delete:
                    trips_to_delete.unlink()

    def _tms_trips_completed(self):
        self.ensure_one()
        trips = self.tms_order_ids
        return bool(trips) and all(trip.stage_id.is_completed for trip in trips)

    def _tms_factor_moves(self):
        self.ensure_one()
        invoices = []
        refunds = []
        for line in self.order_line:
            if not line._tms_needs_factor_adjustment():
                continue
            delta = line._tms_factor_delta()
            if float_compare(delta, 0.0, precision_rounding=0.01) > 0:
                invoices.append((line, delta))
            else:
                refunds.append((line, delta))
        return invoices, refunds

    def _prepare_tms_factor_move(self, move_type, line_deltas):
        self.ensure_one()
        values = self._prepare_invoice()
        values["move_type"] = move_type
        commands = []
        for line, delta in line_deltas:
            line_values = line._prepare_invoice_line()
            line_values["quantity"] = 1.0
            line_values["tms_factor"] = abs(delta)
            label = line_values.get("name") or line.name
            line_values["name"] = self.env._(
                "%(label)s — pickup difference",
                label=label,
            )
            commands.append((0, 0, line_values))
        values["invoice_line_ids"] = commands
        return values

    def _create_tms_factor_adjustment(self):
        """Draft the invoice or credit note for a factor already billed."""
        moves = self.env["account.move"]
        for sale in self:
            if not sale.invoice_ids or not sale._tms_trips_completed():
                continue
            invoices, refunds = sale._tms_factor_moves()
            for move_type, line_deltas in (
                ("out_invoice", invoices),
                ("out_refund", refunds),
            ):
                if not line_deltas:
                    continue
                move = self.env["account.move"].create(
                    sale._prepare_tms_factor_move(move_type, line_deltas)
                )
                moves |= move
                document = self.env._("invoice")
                if move_type == "out_refund":
                    document = self.env._("credit note")
                sale.message_post(
                    body=self.env._(
                        "Trip completion changed the billed factor. "
                        "Draft %(document)s %(name)s covers the difference.",
                        document=document,
                        name=move.display_name,
                    )
                )
        return moves
