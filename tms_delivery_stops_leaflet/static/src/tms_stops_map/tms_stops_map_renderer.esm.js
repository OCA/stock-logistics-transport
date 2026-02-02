/** @odoo-module **/
/*
 * Copyright (C) 2026 KMEE (https://kmee.com.br)
 * @author Luis Felipe Mileo <mileo@kmee.com.br>
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
 */

import {LeafletMapRenderer} from "@web_view_leaflet_map/leaflet_map_view/leaflet_map_renderer.esm";
import {RoutingRenderer} from "@web_leaflet_routing/components/routing_renderer.esm";
import {SelectablePinList} from "./selectable_pin_list.esm";

/**
 * TmsStopsMapRenderer extends LeafletMapRenderer with:
 * - SelectablePinList component for stop selection
 * - OSRM routing support via RoutingRenderer
 * - Support for creating orders from selected stops
 */
export class TmsStopsMapRenderer extends LeafletMapRenderer {
    static template = "tms_delivery_stops_leaflet.TmsStopsMapRenderer";
    static components = {
        ...LeafletMapRenderer.components,
        PinList: SelectablePinList,
    };

    setup() {
        super.setup();
        this.routingRenderer = null;
    }

    /**
     * Override renderRouteLines to use OSRM routing via RoutingRenderer.
     * This method is called by renderMarkers() when routing="1" is set.
     */
    renderRouteLines() {
        // Initialize RoutingRenderer on first call (map is ready at this point)
        if (!this.routingRenderer && this.leafletMap) {
            this.routingRenderer = new RoutingRenderer(this.leafletMap);
        }

        if (!this.routingRenderer) {
            // Fallback to straight lines if initialization failed
            return super.renderRouteLines();
        }

        // Use RoutingRenderer to draw routes with OSRM
        this.routingRenderer.renderRoutes(this.records, {
            groupBy: this.groupBy,
            sequenceField: "sequence",
            latitudeField: this.fieldLatitude,
            longitudeField: this.fieldLongitude,
            useRealRouting: true,
            skipUnassigned: true,
            unassignedGroupName: this.unassignedGroupName || "Sem Viagem",
            validateCoordinates: this.validateCoordinates.bind(this),
        });
    }

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
        if (this.props.model && this.props.model.reload) {
            await this.props.model.reload();
            this.renderMarkers();
        }
    }
}
