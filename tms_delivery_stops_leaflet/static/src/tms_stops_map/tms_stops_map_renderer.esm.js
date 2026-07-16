/** @odoo-module **/
/*
 * Copyright (C) 2026 KMEE (https://kmee.com.br)
 * @author Luis Felipe Mileo <mileo@kmee.com.br>
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
 */

/* global L, console */

import {LeafletMapRenderer} from "@web_view_leaflet_map/leaflet_map_view/leaflet_map_renderer.esm";
import {RoutingRenderer} from "@web_leaflet_routing/components/routing_renderer.esm";
import {SelectablePinList} from "./selectable_pin_list.esm";

/**
 * TmsStopsMapRenderer extends LeafletMapRenderer with:
 * - SelectablePinList component for stop selection
 * - OSRM routing support via RoutingRenderer
 * - Support for creating orders from selected stops
 * - Sequential numbering for all stops (origin, delivery, destination)
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
     * Get stop type badge label for display.
     * Simple switch by stop_type.
     * @param {Object} record - Stop record
     * @returns {String} Badge label (start, stop, end)
     */
    _getStopTypeBadgeLabel(record) {
        const stopType = record.stop_type;
        switch (stopType) {
            case "origin":
                return "start";
            case "destination":
                return "end";
            default:
                return "stop";
        }
    }

    /**
     * Get stop type badge CSS class.
     * Simple switch by stop_type.
     * @param {Object} record - Stop record
     * @returns {String} Bootstrap badge class
     */
    _getStopTypeBadgeClass(record) {
        const stopType = record.stop_type;
        switch (stopType) {
            case "origin":
                return "bg-info";
            case "destination":
                return "bg-success";
            default:
                return "bg-secondary";
        }
    }

    /**
     * Override preparePopUpData to match sidebar layout with badge, weight/volume.
     * @param {Object} record - The record object containing marker data
     * @param {Number} index - The marker index
     * @returns {String}
     */
    preparePopUpData(record, index) {
        const title = record[this.fieldTitle] || record.display_name || "";
        const address = record[this.fieldAddress] || "";
        const lat = record[this.fieldLatitude];
        const lng = record[this.fieldLongitude];
        const weight = record.weight || 0;
        const volume = record.volume || 0;

        // Build navigation URL
        const googleMapsUrl = `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`;

        // Get badge info - simple switch by stop_type
        const badgeLabel = this._getStopTypeBadgeLabel(record);
        const badgeClass = this._getStopTypeBadgeClass(record);

        // Navigation button HTML
        const navButton = this.enableNavigation
            ? `<a href="${googleMapsUrl}" target="_blank" class="btn btn-sm btn-primary" title="Navegar">
                   <i class="fa fa-location-arrow"></i>
               </a>`
            : "";

        const html = `
            <div class='o_map_popup o_tms_stop_popup'>
                <div class='o_popup_row' data-res-id='${record.id}'>
                    <!-- Left: Number + Content -->
                    <div class="o_popup_left">
                        <span class="o_popup_number">${index + 1}</span>
                        <div class="o_popup_content o_map_selector">
                            <div class="o_popup_title"><b>${this.escapeHtml(title)}</b></div>
                            ${address ? `<div class="o_popup_address text-muted small">${this.escapeHtml(address)}</div>` : ""}
                        </div>
                    </div>
                    <!-- Right: Badge + Weight/Volume + Navigate -->
                    <div class="o_popup_right">
                        <div class="o_popup_metrics">
                            <span class="badge ${badgeClass} o_stop_type_badge">${badgeLabel}</span>
                            <div class="o_popup_volume text-muted small">
                                <i class="fa fa-cube"></i> ${volume.toFixed(2)}
                            </div>
                            <div class="o_popup_weight text-muted small">
                                <i class="fa fa-balance-scale"></i> ${weight.toFixed(1)}
                            </div>
                        </div>
                        ${navButton}
                    </div>
                </div>
            </div>
        `;
        return html;
    }

    /**
     * Get numeric stop type order, handling various input types.
     * @param {Object} record - The record object
     * @returns {Number} 0 for origin, 1 for delivery, 2 for destination
     */
    _getStopTypeOrder(record) {
        // First try stop_type_order field
        if (record.stop_type_order !== undefined && record.stop_type_order !== null) {
            const order = Number(record.stop_type_order);
            if (!isNaN(order)) {
                return order;
            }
        }
        // Fallback: derive from stop_type
        const stopType = record.stop_type;
        if (stopType === "origin") return 0;
        if (stopType === "destination") return 2;
        return 1; // Delivery or unknown
    }

    /**
     * Sort records by stop_type_order then sequence.
     * Order: origin (0) -> delivery (1) -> destination (2)
     * @param {Array} records - Array of records to sort
     * @returns {Array} Sorted array
     */
    sortRecordsByStopOrder(records) {
        const sorted = [...records].sort((a, b) => {
            // Primary sort by stop_type_order (0=origin, 1=delivery, 2=destination)
            const aOrder = this._getStopTypeOrder(a);
            const bOrder = this._getStopTypeOrder(b);
            if (aOrder !== bOrder) {
                return aOrder - bOrder;
            }
            // Secondary sort by sequence
            return (a.sequence || 0) - (b.sequence || 0);
        });

        // Debug logging
        console.debug(
            "[TmsStopsMapRenderer] Sorted stops:",
            sorted.map((r) => ({
                id: r.id,
                stop_type: r.stop_type,
                stop_type_order: r.stop_type_order,
                computed_order: this._getStopTypeOrder(r),
                sequence: r.sequence,
            }))
        );

        return sorted;
    }

    /**
     * Get records filtered to avoid duplicate origin/destination markers.
     * When origin and destination are at the same location, show only one marker.
     * Returns records sorted in route order: origin -> deliveries -> destination.
     * Used for MARKERS only - for routing, use getRecordsForRouting().
     * @returns {Array}
     */
    getFilteredRecords() {
        const records = this.records;

        // Group by order_id
        const byOrder = {};
        for (const r of records) {
            const orderId = r.order_id
                ? Array.isArray(r.order_id)
                    ? r.order_id[0]
                    : r.order_id
                : "unassigned";
            if (!byOrder[orderId]) byOrder[orderId] = [];
            byOrder[orderId].push(r);
        }

        // Filter out destination if same location as origin, then sort
        const result = [];
        for (const stops of Object.values(byOrder)) {
            const origin = stops.find((s) => s.stop_type === "origin");
            const destination = stops.find((s) => s.stop_type === "destination");

            // Check if same location (same coordinates) - filter out destination if so
            const sameLocation =
                origin &&
                destination &&
                origin.latitude === destination.latitude &&
                origin.longitude === destination.longitude;
            const filteredStops = sameLocation
                ? stops.filter((s) => s.stop_type !== "destination")
                : stops;

            // Sort stops in correct order: origin -> delivery -> destination
            const sortedStops = this.sortRecordsByStopOrder(filteredStops);

            result.push(...sortedStops);
        }
        return result;
    }

    /**
     * Get records for routing - keeps all stops including destination.
     * This ensures routes close the loop back to origin when destination == origin.
     * Returns records sorted in route order: origin -> deliveries -> destination.
     * @returns {Array}
     */
    getRecordsForRouting() {
        const records = this.records;

        // Group by order_id
        const byOrder = {};
        for (const r of records) {
            const orderId = r.order_id
                ? Array.isArray(r.order_id)
                    ? r.order_id[0]
                    : r.order_id
                : "unassigned";
            if (!byOrder[orderId]) byOrder[orderId] = [];
            byOrder[orderId].push(r);
        }

        // Sort all stops (keep destination for routing to close the loop)
        const result = [];
        for (const stops of Object.values(byOrder)) {
            const sortedStops = this.sortRecordsByStopOrder(stops);
            result.push(...sortedStops);
        }
        return result;
    }

    /**
     * Override renderMarkers to use filtered records.
     */
    renderMarkers() {
        if (!this.leafletMap) {
            return;
        }

        if (this.mainLayer) {
            this.leafletMap.removeLayer(this.mainLayer);
        }

        this.mainLayer = L.markerClusterGroup();
        this.markersById = {};

        // Use filtered records to handle duplicate origin/destination
        const filteredRecords = this.getFilteredRecords();

        // Use sequential numbering for ALL stops (1, 2, 3...)
        let stopIndex = 0;
        for (const record of filteredRecords) {
            const index = stopIndex++;
            const marker = this.prepareMarker(record, index);
            if (marker) {
                this.mainLayer.addLayer(marker);
                this.markersById[record.id] = marker;
            }
        }

        const bounds = this.mainLayer.getBounds();
        if (bounds.isValid()) {
            this.leafletMap.fitBounds(bounds.pad(0.1));
        }

        this.leafletMap.addLayer(this.mainLayer);

        // Draw route lines if routing is enabled
        if (this.enableRouting && filteredRecords.length > 1) {
            this.renderRouteLines();
        }
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
        // Use getRecordsForRouting() to include destination (closes loop for circular routes)
        this.routingRenderer.renderRoutes(this.getRecordsForRouting(), {
            groupBy: this.groupBy,
            sequenceField: "sequence",
            stopTypeField: "stop_type",
            stopTypeOrderField: "stop_type_order",
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

    /**
     * Override onPinClick to handle filtered-out stops.
     * When destination is filtered (same location as origin), open origin's popup.
     * @param {Object} record - The record clicked in the sidebar
     */
    onPinClick(record) {
        const lat = record[this.fieldLatitude];
        const lng = record[this.fieldLongitude];

        if (!this.validateCoordinates(lat, lng)) {
            return;
        }

        // Center map on the record
        this.leafletMap.setView([lat, lng], 16);

        // Try to find the marker for this record
        let marker = this.markersById[record.id];

        // If no marker found (e.g., destination filtered out), find a marker at same location
        if (!marker && record.stop_type === "destination") {
            // Look for origin marker at the same coordinates
            for (const m of Object.values(this.markersById)) {
                const markerLatLng = m.getLatLng();
                if (
                    Math.abs(markerLatLng.lat - lat) < 0.0001 &&
                    Math.abs(markerLatLng.lng - lng) < 0.0001
                ) {
                    marker = m;
                    break;
                }
            }
        }

        if (marker) {
            marker.openPopup();
        }
    }
}
