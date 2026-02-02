/** @odoo-module **/
/*
 * Copyright (C) 2025 KMEE (https://kmee.com.br)
 * @author Luis Felipe Mileo <mileo@kmee.com.br>
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
 */

import {registry} from "@web/core/registry";
import {leafletMapView} from "@web_view_leaflet_map/leaflet_map_view/leaflet_map_view.esm";
import {TmsStopsMapModel} from "./tms_stops_map_model.esm";
import {TmsStopsMapRenderer} from "./tms_stops_map_renderer.esm";

/**
 * TMS Stops Map View extends the base leaflet_map view with TMS-specific features.
 *
 * Following Odoo Enterprise pattern (similar to stock_map extending map):
 * - Uses spread syntax to inherit from leafletMapView
 * - Overrides Model and Renderer with TMS-specific implementations
 * - Registered as "tms_stops_map" for use with js_class attribute
 */
export const tmsStopsMapView = {
    ...leafletMapView,
    Model: TmsStopsMapModel,
    Renderer: TmsStopsMapRenderer,
};

// Register as a separate view type (NO force:true!)
registry.category("views").add("tms_stops_map", tmsStopsMapView);
