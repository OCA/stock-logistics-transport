# Copyright (C) 2025 KMEE (https://kmee.com.br)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class TMSOrderStop(models.Model):
    """Extend TMS Order Stop with additional fields for Leaflet map display."""

    _inherit = "tms.order.stop"

    # Additional display fields for map popups
    order_name = fields.Char(
        related="order_id.name",
        string="Order Name",
        store=True,
    )
    partner_name = fields.Char(
        related="partner_id.display_name",
        string="Partner Name",
        store=True,
    )
    partner_phone = fields.Char(
        related="partner_id.phone",
        string="Phone",
    )
    partner_mobile = fields.Char(
        related="partner_id.mobile",
        string="Mobile",
    )
    state_display = fields.Char(
        compute="_compute_state_display",
        string="Status",
    )
    map_popup_info = fields.Html(
        compute="_compute_map_popup_info",
    )

    @api.depends("state")
    def _compute_state_display(self):
        """Compute human-readable state for map display."""
        state_labels = dict(self._fields["state"].selection)
        for stop in self:
            stop.state_display = state_labels.get(stop.state, stop.state)

    @api.depends(
        "partner_id",
        "sequence",
        "state",
        "weight",
        "volume",
        "package_count",
        "scheduled_date",
    )
    def _compute_map_popup_info(self):
        """Compute rich popup content for map markers."""
        for stop in self:
            parts = []

            if stop.scheduled_date:
                parts.append(
                    f"<strong>Scheduled:</strong> "
                    f"{stop.scheduled_date.strftime('%d/%m/%Y %H:%M')}"
                )

            if stop.package_count:
                parts.append(f"<strong>Packages:</strong> {stop.package_count}")

            if stop.weight:
                parts.append(f"<strong>Weight:</strong> {stop.weight:.2f} kg")

            if stop.volume:
                parts.append(f"<strong>Volume:</strong> {stop.volume:.3f} m³")

            stop.map_popup_info = "<br/>".join(parts) if parts else ""

    def action_open_in_map(self):
        """Open this stop and all stops from the same order in a map view."""
        self.ensure_one()
        if self.order_id:
            return self.order_id.action_open_stops_map()

        # Single stop without order
        return {
            "type": "ir.actions.act_window",
            "name": f"Stop: {self.display_name}",
            "res_model": "tms.order.stop",
            "view_mode": "leaflet_map,form",
            "domain": [("id", "=", self.id)],
        }

    def action_resequence_stops(self, stop_id, target_order_id, ref_stop_id=None):
        """
        Reorder a stop within the same trip or move to another trip.

        This method enables drag-and-drop reordering of delivery stops
        in the map view sidebar. Supports bidirectional moves:
        - From "Sem Viagem" to a trip: assigns order_id
        - From a trip to "Sem Viagem": removes order_id (sets to False)
        - Between trips: changes order_id

        Args:
            stop_id: ID of the stop being moved
            target_order_id: ID of the target trip (None/False for "Sem Viagem")
            ref_stop_id: ID of the stop after which to insert (None = first)

        Returns:
            dict with operation result
        """
        # Validate stop_id
        if not stop_id:
            return {"success": False, "error": "No stop ID provided"}

        stop = self.browse(stop_id)
        if not stop.exists():
            return {"success": False, "error": f"Stop {stop_id} not found"}

        source_order = stop.order_id
        target_order = False

        # Handle target_order_id (can be None/False for "Sem Viagem")
        if target_order_id:
            target_order = self.env["tms.order"].browse(target_order_id)
            if not target_order.exists():
                return {
                    "success": False,
                    "error": f"Target order {target_order_id} not found",
                }

        # Determine new sequence
        if ref_stop_id:
            ref_stop = self.browse(ref_stop_id)
            if ref_stop.exists():
                new_sequence = ref_stop.sequence + 1
            else:
                new_sequence = 10
        elif target_order:
            # Insert at the beginning of target order
            first_stop = target_order.stop_ids.sorted("sequence")[:1]
            new_sequence = (first_stop.sequence - 10) if first_stop else 10
        else:
            # Moving to "Sem Viagem" - use default sequence
            new_sequence = 10

        # Update stop
        vals = {"sequence": new_sequence}

        # Handle order assignment/removal
        source_order_id = source_order.id if source_order else False
        target_order_id_val = target_order.id if target_order else False

        if source_order_id != target_order_id_val:
            vals["order_id"] = target_order_id_val

        stop.write(vals)

        # Renumber sequences to avoid conflicts
        if target_order:
            self._renumber_sequences(target_order)
        if source_order and source_order.id != target_order_id_val:
            self._renumber_sequences(source_order)

        return {"success": True}

    def _renumber_sequences(self, order):
        """Renumber stop sequences in increments of 10."""
        for idx, stop in enumerate(order.stop_ids.sorted("sequence")):
            new_seq = (idx + 1) * 10
            if stop.sequence != new_seq:
                stop.sequence = new_seq
