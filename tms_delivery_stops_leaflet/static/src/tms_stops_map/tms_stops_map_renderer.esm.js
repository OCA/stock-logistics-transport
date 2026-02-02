/** @odoo-module **/
/*
 * Copyright (C) 2026 KMEE (https://kmee.com.br)
 * @author Luis Felipe Mileo <mileo@kmee.com.br>
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
 */

import {LeafletMapRenderer} from "@web_view_leaflet_map/leaflet_map_view/leaflet_map_renderer.esm";
import {SelectablePinList} from "./selectable_pin_list.esm";

/**
 * TmsStopsMapRenderer extends LeafletMapRenderer with:
 * - SelectablePinList component for stop selection
 * - Support for creating orders from selected stops
 */
export class TmsStopsMapRenderer extends LeafletMapRenderer {
    static template = "tms_delivery_stops_leaflet.TmsStopsMapRenderer";
    static components = {
        ...LeafletMapRenderer.components,
        PinList: SelectablePinList,
    };

    /**
     * Override to use SelectablePinList instead of default PinList.
     * @returns {Component} SelectablePinList component class
     */
    get PinListComponent() {
        return SelectablePinList;
    }

    /**
     * Handler to reload data after wizard closes.
     * This is called when the "Create Order" wizard completes.
     */
    async onDataReload() {
        // Reload data through the model
        if (this.props.model && this.props.model.reload) {
            await this.props.model.reload();
            // Force re-render of markers after data reload
            this.renderMarkers();
        }
    }
}
