# Copyright (C) 2025 KMEE (https://kmee.com.br)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class TMSRouteOptimizer(models.TransientModel):
    """
    Extend TMS Route Optimizer to read the configured distance provider
    from res.config.settings and set the use_osrm flag accordingly.

    This module bridges the UI configuration (tms.distance_provider) with
    the OSRM module's use_osrm field. When the OSRM module is installed,
    the configured provider takes precedence over the wizard's default.
    """

    _inherit = "tms.route.optimizer"

    def _compute_distance_matrix(self, locations):
        """
        Read the configured distance provider and ensure the optimizer
        state is consistent before delegating to super().
        """
        provider = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("tms.distance_provider", "haversine")
        )

        # If the OSRM module is installed, sync use_osrm with config
        if hasattr(self, "use_osrm"):
            if provider == "osrm" and not self.use_osrm:
                self.use_osrm = True
            elif provider == "haversine" and self.use_osrm:
                self.use_osrm = False

        return super()._compute_distance_matrix(locations)
