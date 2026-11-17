# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class TMSOrder(models.Model):
    _inherit = "tms.order"

    def _distance_between_locations(self, origin, destination, uom):
        """Road distance from the routing provider, then the great-circle."""
        self.ensure_one()
        route_model = self.env["tms.route"]
        if origin and destination and route_model._routing_provider_ready():
            try:
                distance, provider_uom = route_model._distance_between_partners(
                    origin, destination
                )
            except UserError as error:
                _logger.info(
                    "No road distance between %s and %s: %s",
                    origin.display_name,
                    destination.display_name,
                    error,
                )
            except Exception:
                _logger.exception(
                    "Routing provider failed between %s and %s",
                    origin.display_name,
                    destination.display_name,
                )
            else:
                if provider_uom and uom and provider_uom != uom:
                    distance = provider_uom._compute_quantity(distance, uom)
                    return distance, uom
                return distance, provider_uom or uom
        return super()._distance_between_locations(origin, destination, uom)
