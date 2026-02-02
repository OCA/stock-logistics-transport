/** @odoo-module **/
/*
 * Copyright (C) 2026 KMEE (https://kmee.com.br)
 * @author Luis Felipe Mileo <mileo@kmee.com.br>
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
 */

import {TmsStopsMapModel} from "./tms_stops_map_model.esm";
import {TmsStopsMapRenderer} from "./tms_stops_map_renderer.esm";
import {registry} from "@web/core/registry";

const leafletMapView = registry.category("views").get("leaflet_map");

/**
 * Register the tms_stops_leaflet_map view.
 * This view extends the base leaflet_map with:
 * - Custom model for TMS stop resequencing
 * - Custom renderer with selection support
 *
 * Used via js_class="tms_stops_leaflet_map" in the XML view definition.
 */
export const tmsStopsMapView = {
    ...leafletMapView,
    Model: TmsStopsMapModel,
    Renderer: TmsStopsMapRenderer,
};

registry.category("views").add("tms_stops_leaflet_map", tmsStopsMapView);
