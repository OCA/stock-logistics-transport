# Copyright (C) 2025 KMEE (https://kmee.com.br)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """
    Migrate TMS OSRM configuration to shared Leaflet configuration if needed.

    This ensures that existing TMS installations using tms.osrm_server_url
    will also have the shared leaflet.osrm_url parameter set.
    """
    config = env["ir.config_parameter"].sudo()

    tms_url = config.get_param("tms.osrm_server_url")
    leaflet_url = config.get_param("leaflet.osrm_url")

    if tms_url and not leaflet_url:
        _logger.info(
            "Migrating OSRM URL from tms.osrm_server_url to leaflet.osrm_url: %s",
            tms_url,
        )
        config.set_param("leaflet.osrm_url", tms_url)
