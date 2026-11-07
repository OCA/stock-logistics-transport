# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
from pathlib import Path

from odoo import api, models

BRAND_LOGOS = (
    "brand_freightliner",
    "brand_kenworth",
    "brand_peterbilt",
    "brand_mack",
    "brand_international",
    "brand_scania",
    "brand_man",
    "brand_daf",
    "brand_iveco",
    "brand_hino",
    "brand_setra",
    "brand_irizar",
    "brand_marcopolo",
    "brand_yutong",
    "brand_prevost",
    "brand_mci",
    "brand_new_flyer",
    "brand_van_hool",
    "brand_alexander_dennis",
)


class FleetVehicleModelBrand(models.Model):
    _inherit = "fleet.vehicle.model.brand"

    @api.model
    def _tms_load_brand_logos(self):
        """Set manufacturer logos that were not loaded with the brand record.

        Brand data is noupdate, so an already installed database does not pick
        up image changes from XML.
        """
        img_dir = Path(__file__).resolve().parent.parent / "static" / "img"
        for xmlid in BRAND_LOGOS:
            brand = self.env.ref(f"tms.{xmlid}", raise_if_not_found=False)
            if not brand or brand.image_128:
                continue
            path = img_dir / f"{xmlid}-image.png"
            if not path.is_file():
                continue
            brand.image_128 = base64.b64encode(path.read_bytes())
