# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    tms_stop_id = fields.Many2one(
        comodel_name="tms.order.stop",
        string="TMS Stop",
        ondelete="set null",
    )
    tms_order_id = fields.Many2one(
        comodel_name="tms.order",
        string="TMS Order",
        compute="_compute_tms_order_id",
        store=True,
        readonly=True,
    )
    has_tms_stop = fields.Boolean(
        compute="_compute_has_tms_stop",
        store=False,
    )
    package_count = fields.Integer(
        compute="_compute_package_count",
    )

    @api.depends("tms_stop_id", "tms_stop_id.order_id")
    def _compute_tms_order_id(self):
        for picking in self:
            picking.tms_order_id = picking.tms_stop_id.order_id

    def _compute_has_tms_stop(self):
        for picking in self:
            picking.has_tms_stop = bool(picking.tms_stop_id)

    @api.depends("move_line_ids.result_package_id")
    def _compute_package_count(self):
        for picking in self:
            picking.package_count = len(picking.move_line_ids.result_package_id)

    def action_confirm(self):
        res = super().action_confirm()
        for picking in self:
            picking._auto_create_tms_stop()
        return res

    def write(self, vals):
        res = super().write(vals)
        if "state" in vals:
            for picking in self:
                picking._sync_tms_stop_state()
        return res

    def _sync_tms_stop_state(self):
        self.ensure_one()
        stop = self.tms_stop_id
        if not stop:
            return

        if self.state == "assigned":
            # Keep draft as-is; do not downgrade scheduled/delivered.
            return

        if self.state == "done":
            if stop.state in ("delivered", "scheduled"):
                return
            stop.write({"state": "scheduled"})
            return

        if self.state == "cancel":
            if stop.state == "delivered":
                return
            stop.write({"state": "skipped"})

    def _auto_create_tms_stop(self):
        self.ensure_one()
        if not self._should_create_tms_stop():
            return False
        return self._create_tms_stop()

    def _should_create_tms_stop(self):
        self.ensure_one()
        if self.tms_stop_id:
            return False
        if self.picking_type_code != "outgoing":
            return False
        if getattr(self, "is_return_picking", False):
            return False
        carrier = self.carrier_id
        if not carrier or not carrier.is_internal_carrier:
            return False
        if not carrier.auto_create_stops:
            return False
        return True

    def action_create_tms_stop(self):
        self.ensure_one()
        if self.tms_stop_id:
            return self.action_open_tms_stop()
        if not self.carrier_id or not self.carrier_id.is_internal_carrier:
            raise UserError(_("This picking does not use an internal carrier."))
        return self._create_tms_stop()

    def action_open_tms_stop(self):
        self.ensure_one()
        if not self.tms_stop_id:
            raise UserError(_("There is no TMS stop linked to this picking."))
        return {
            "type": "ir.actions.act_window",
            "name": _("TMS Stop"),
            "res_model": "tms.order.stop",
            "view_mode": "form",
            "res_id": self.tms_stop_id.id,
            "target": "current",
        }

    def action_create_tms_order(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "tms_delivery_stops_delivery.action_create_tms_order_wizard"
        )
        action["context"] = dict(
            self.env.context,
            active_model="stock.picking",
            active_ids=self.ids,
        )
        return action

    def _create_tms_stop(self):
        self.ensure_one()
        if self.picking_type_code != "outgoing":
            raise UserError(_("Only outgoing pickings can create TMS stops."))

        partner = self.partner_id
        has_geo = bool(partner.partner_latitude and partner.partner_longitude)
        weight = self.weight or 0.0
        volume = self._get_picking_volume()
        package_count = self._get_picking_package_count()

        stop_vals = {
            "partner_id": partner.id,
            "weight": weight,
            "volume": volume,
            "package_count": package_count,
            "scheduled_date": self.scheduled_date,
            "company_id": self.company_id.id,
            "state": "draft",
            "picking_id": self.id,
        }
        stop = self.env["tms.order.stop"].create(stop_vals)
        self.tms_stop_id = stop.id

        self._post_stop_created_message(has_geo)
        if not has_geo:
            _logger.warning(
                "Partner %s missing geolocation for picking %s.",
                partner.display_name,
                self.name,
            )
        else:
            _logger.info("Created TMS stop %s for picking %s.", stop.id, self.name)

        return stop

    def _post_stop_created_message(self, has_geo):
        self.ensure_one()
        if has_geo:
            body = _("TMS stop created for this picking.")
            self.message_post(body=body, message_type="notification")
            return

        warning = _(
            "TMS stop created, but the partner has no geolocation. "
            "Please geolocate the partner to enable route optimization."
        )
        self.message_post(body=warning, message_type="notification")

    def _get_picking_volume(self):
        self.ensure_one()
        return self.volume

    def _get_picking_package_count(self):
        self.ensure_one()
        return len(self.move_line_ids.result_package_id)
