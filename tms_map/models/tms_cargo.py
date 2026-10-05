# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models
from odoo.exceptions import AccessError, UserError


class TmsCargo(models.Model):
    _inherit = "tms.cargo"

    def _tms_map_location(self):
        """Place unassigned cargo at the sale origin, or the trip origin."""
        self.ensure_one()
        if "sale_line_id" in self._fields and self.sale_line_id:
            line = self.sale_line_id
            if "tms_origin_id" in line._fields and line.tms_origin_id:
                return line.tms_origin_id
        return self.origin_id

    @api.model
    def tms_map_unassigned_clusters(self):
        clusters = {}
        cargo = self.search([("state", "=", "unassigned")])
        for line in cargo:
            partner = line._tms_map_location()
            key = partner.id or 0
            cluster = clusters.get(key)
            if not cluster:
                cluster = {
                    "partner_id": partner.id or False,
                    "name": partner.display_name
                    if partner
                    else self.env._("No location"),
                    "latitude": False,
                    "longitude": False,
                    "cargo": [],
                }
                if partner and (
                    partner.partner_latitude or partner.partner_longitude
                ):
                    cluster["latitude"] = partner.partner_latitude
                    cluster["longitude"] = partner.partner_longitude
                clusters[key] = cluster
            cluster["cargo"].append({"id": line.id, "name": line.name})
        return list(clusters.values())

    def tms_map_assign(self, order_id):
        """Place unassigned cargo on a trip that has not started."""
        if not self.env.user.has_group("tms.group_tms_user"):
            raise AccessError(self.env._("You cannot assign cargo."))
        order = self.env["tms.order"].browse(order_id).exists()
        if not order or order.start_trip or order.end_trip:
            raise UserError(self.env._("Choose a trip that has not started."))
        cargo = self.filtered(
            lambda line: line.state == "unassigned"
            and not line.order_id.start_trip
            and not line.order_id.end_trip
        )
        if not cargo:
            raise UserError(
                self.env._("Only unassigned cargo can be placed on a trip.")
            )
        cargo.sudo().write({"order_id": order.id, "state": "planned"})
        return True
