# Copyright (C) 2024 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from markupsafe import Markup

from odoo import _, api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    tms_order_ids = fields.Many2many(
        "tms.order",
        compute="_compute_tms_order_ids",
        string="Transport orders associated to this sale",
        copy=False,
    )
    tms_order_count = fields.Integer(
        string="Transport Orders", compute="_compute_tms_order_ids"
    )

    has_tms_order = fields.Boolean(compute="_compute_has_tms_order")

    def action_view_trip_sale_order_line(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order.line.trip",
            "target": "new",
            "view_mode": "form",
            "view_type": "form",
        }

    @api.depends("order_line")
    def _compute_has_tms_order(self):
        for sale in self:
            has_tms_order = any(
                line.product_template_id.tms_trip
                and line.product_template_id.trip_product_type == "trip"
                for line in sale.order_line
            )
            sale.has_tms_order = has_tms_order

    @api.depends("order_line")
    def _compute_tms_order_ids(self):
        for sale in self:
            tms = self.env["tms.order"].search(
                [
                    "|",
                    ("sale_id", "=", sale.id),
                    ("sale_line_id", "in", sale.order_line.ids),
                ]
            )
            sale.tms_order_ids = tms
            sale.tms_order_count = len(sale.tms_order_ids)

    def _tms_generate_line_tms_orders(self, new_tms_sol):
        """
        Generate TMS Orders for the given sale order lines.

        Override this method to filter lines to generate TMS Orders for.
        """
        self.ensure_one()
        new_tms_orders = self.env["tms.order"]

        for line in new_tms_sol:
            for i in range(int(line.product_uom_qty) - len(line.tms_order_ids)):
                vals = line._prepare_line_tms_values(line)
                tms_by_line = self.env["tms.order"].sudo().create(vals)
                line.write({"tms_order_ids": [(4, tms_by_line.id)]})
                new_tms_orders |= tms_by_line
                i = i  # pre-commit

        return new_tms_orders

    def _tms_generate(self):
        self.ensure_one()
        new_tms_orders = self.env["tms.order"]

        new_tms_line_sol = self.order_line.filtered(
            lambda L: L.product_id.trip_product_type == "trip"
            and len(L.tms_order_ids) != L.product_uom_qty
            and len(L.tms_order_ids) < L.product_uom_qty
        )

        new_tms_orders |= self._tms_generate_line_tms_orders(new_tms_line_sol)

        return new_tms_orders

    def _tms_generation(self):
        """
        Create TMS Orders based on the products' configuration.
        :rtype: list(TMS Orders)
        :return: list of newly created TMS Orders
        """
        created_tms_orders = self.env["tms.order"]

        for sale in self:
            new_tms_orders = self._tms_generate()

            if len(new_tms_orders) > 0:
                created_tms_orders |= new_tms_orders
                sale._post_tms_message(new_tms_orders)

        return created_tms_orders

    def _post_tms_message(self, tms_orders):
        """
        Post messages to the Sale Order and the newly created TMS Orders
        """
        self.ensure_one()
        for tms_order in tms_orders:
            tms_order.message_mail_with_source(
                "mail.message_origin_link",
                render_values={"self": tms_order, "origin": self},
                subtype_id=self.env.ref("mail.mt_note").id,
                author_id=self.env.user.partner_id.id,
            )
            message = _(
                "Transport Order(s) Created: %s",
                Markup(
                    f"""<a href=# data-oe-model=tms.order data-oe-id={tms_order.id}"""
                    f""">{tms_order.name}</a>"""
                ),
            )
            self.message_post(body=message)

    def _action_create_new_trips(self):
        if any(
            sol.product_id.trip_product_type == "trip"
            for sol in self.order_line.filtered(
                lambda x: x.display_type not in ("line_section", "line_note")
            )
        ):
            self._tms_generation()

    def action_view_tms_order(self):
        tms_orders = self.mapped("tms_order_ids")
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "tms.action_tms_dash_order"
        )
        if len(tms_orders) > 1:
            action["domain"] = [("id", "in", tms_orders.ids)]
        elif len(tms_orders) == 1:
            action["views"] = [(self.env.ref("tms.tms_order_view_form").id, "form")]
            action["res_id"] = tms_orders.id
        else:
            action = {"type": "ir.actions.act_window_close"}
        return action

    def remove_lines_with_trips(
        self, initial_trips, initial_line_ids, initial_quantities
    ):
        current_order_line_ids = set(self.order_line.ids)
        removed_lines = initial_line_ids - current_order_line_ids

        if removed_lines:
            trips_to_delete = initial_trips.filtered(
                lambda trip_id: not (trip_id.sale_line_id & self.order_line)
            )
            if trips_to_delete:
                trips_to_delete.unlink()

        for line in self.order_line:
            if line.id in initial_quantities:
                if line.product_uom_qty < initial_quantities[line.id]:
                    trips_to_delete = line.tms_order_ids[:1]
                    if trips_to_delete:
                        trips_to_delete.unlink()

    @api.model
    def create(self, vals):
        order = super().create(vals)
        if "order_line" in vals and order.has_tms_order:
            order._action_create_new_trips()
        return order

    @api.model
    def write(self, vals):
        initial_trips = self.env["tms.order"].search(
            [("sale_line_id", "in", self.order_line.ids)]
        )
        initial_order_line_ids = set(self.order_line.ids)
        initial_quantities = {line.id: line.product_uom_qty for line in self.order_line}

        result = super().write(vals)

        if "order_line" in vals and self.has_tms_order:
            self.remove_lines_with_trips(
                initial_trips, initial_order_line_ids, initial_quantities
            )
            self._action_create_new_trips()

        if "state" in vals:
            if self.state == "sale":
                stage = self.env.ref("tms.tms_stage_order_confirmed")
            elif self.state == "cancel":
                stage = self.env.ref("tms.tms_stage_order_cancelled")
            else:
                stage = self.env.ref("tms.tms_stage_order_draft")

            for line in self.order_line:
                for trip in line.tms_order_ids:
                    trip.stage_id = stage

        return result
