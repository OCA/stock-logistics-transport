# Copyright (C) 2025 KMEE (https://kmee.com.br)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # Distance Provider Configuration
    tms_distance_provider = fields.Selection(
        selection=[
            ("haversine", "Haversine (Straight Line)"),
            ("osrm", "OSRM (Road Network)"),
            ("google", "Google Maps (Premium)"),
        ],
        string="Distance Provider",
        default="haversine",
        config_parameter="tms.distance_provider",
        help="Choose the distance calculation method:\n"
        "- Haversine: Fast, no external service, but uses straight-line distances\n"
        "- OSRM: Free, uses actual road network, requires internet or self-hosted\n"
        "- Google: Paid, most accurate, requires API key",
    )

    tms_distance_fallback_enabled = fields.Boolean(
        string="Enable Fallback",
        default=True,
        config_parameter="tms.distance_fallback_enabled",
        help="If enabled, falls back to Haversine if the selected provider fails.",
    )

    # OSRM Configuration
    tms_osrm_server_url = fields.Char(
        string="OSRM Server URL",
        default="https://router.project-osrm.org",
        config_parameter="tms.osrm_server_url",
        help="OSRM routing server URL.\n"
        "Default: https://router.project-osrm.org (public demo server)\n"
        "For production, consider self-hosting OSRM.",
    )

    tms_osrm_profile = fields.Selection(
        selection=[
            ("driving", "Driving"),
            ("walking", "Walking"),
            ("cycling", "Cycling"),
        ],
        string="OSRM Profile",
        default="driving",
        config_parameter="tms.osrm_profile",
        help="Routing profile for OSRM distance calculations.",
    )

    # Google Maps Configuration
    tms_google_api_key = fields.Char(
        string="Google Maps API Key",
        config_parameter="tms.google_api_key",
        help="Google Maps Distance Matrix API key.\n"
        "Required for Google distance provider.",
    )

    tms_google_travel_mode = fields.Selection(
        selection=[
            ("driving", "Driving"),
            ("walking", "Walking"),
            ("bicycling", "Bicycling"),
            ("transit", "Transit"),
        ],
        string="Google Travel Mode",
        default="driving",
        config_parameter="tms.google_travel_mode",
        help="Travel mode for Google distance calculations.",
    )

    # Performance Settings
    tms_batch_size = fields.Integer(
        string="Batch Size",
        default=25,
        config_parameter="tms.distance_batch_size",
        help="Maximum number of locations per API request.\n"
        "OSRM and Google have limits on waypoints per request.",
    )

    tms_cache_enabled = fields.Boolean(
        string="Enable Distance Cache",
        default=True,
        config_parameter="tms.distance_cache_enabled",
        help="Cache distance calculations to improve performance.\n"
        "See tms_route_optimizer_distance_cache module for persistent caching.",
    )

    tms_cache_ttl_hours = fields.Integer(
        string="Cache TTL (hours)",
        default=168,
        config_parameter="tms.distance_cache_ttl_hours",
        help="Time-to-live for cached distances in hours.\n"
        "Default: 168 hours (1 week)",
    )
