/** @odoo-module **/

/* global L */

import {LeafletMapRenderer} from "@web_view_leaflet_map/leaflet_map_view/leaflet_map_renderer.esm";
import {DraggablePinList} from "@web_view_leaflet_map/components/pin-list/draggable_pin_list.esm";
import {RoutingRenderer} from "@web_leaflet_routing/components/routing_renderer.esm";

const STATE_COLORS = {
    draft: "#6c757d",
    scheduled: "#007bff",
    delivered: "#28a745",
    skipped: "#dc3545",
    unassigned: "#fd7e14", // Orange - stops without order (Sem Viagem)
};

/**
 * TmsStopsMapRenderer extends LeafletMapRenderer with TMS-specific features:
 * - Status-based marker colors for tms.order.stop
 * - OSRM routing for real road-based routes
 * - Enhanced popups with delivery info
 * - Drag-and-drop stop reordering via DraggablePinList
 */
export class TmsStopsMapRenderer extends LeafletMapRenderer {
    static template = "tms_delivery_stops_leaflet.TmsStopsMapRenderer";
    static components = {
        ...LeafletMapRenderer.components,
        PinList: DraggablePinList,
    };

    setup() {
        super.setup();
        this.stateColors = STATE_COLORS;
        this.routingRenderer = null;
    }

    /**
     * Override to initialize RoutingRenderer after map is created.
     */
    initMap() {
        super.initMap();
        if (this.leafletMap && this.enableRouting) {
            this.routingRenderer = new RoutingRenderer(this.leafletMap);
        }
    }

    /**
     * Use DraggablePinList for TMS stops.
     */
    get PinListComponent() {
        return DraggablePinList;
    }

    /**
     * Check if a record has a valid order_id (is assigned to a trip).
     */
    _hasOrderId(record) {
        const orderId = record.order_id;
        if (!orderId) return false;
        return Array.isArray(orderId) ? Boolean(orderId[0]) : Boolean(orderId);
    }

    /**
     * Override to create markers with state-based colors for stops.
     * Unassigned stops (without order_id) use circle markers instead of pins.
     */
    prepareMarkerOptions(record, index) {
        const title = record[this.fieldTitle] || "";
        const result = {
            title: title,
            alt: title,
            riseOnHover: true,
        };

        // Check if stop is unassigned (no order_id)
        const hasOrder = this._hasOrderId(record);

        if (this.showNumberedMarkers) {
            // For tms.order.stop, use state-based colors
            if (this.resModel === "tms.order.stop") {
                if (!hasOrder) {
                    // Unassigned stops: use circle marker (no number)
                    result.icon = this.createCircleMarker(this.stateColors.unassigned);
                } else if (record.state) {
                    const color =
                        this.stateColors[record.state] || this.stateColors.draft;
                    result.icon = this.createNumberedMarker(
                        record.sequence || index + 1,
                        color
                    );
                } else {
                    result.icon = this.createNumberedMarker(
                        record.sequence || index + 1,
                        this.stateColors.draft
                    );
                }
            } else {
                const groupName = this.getGroupName(record);
                const color = groupName ? this.getGroupColor(groupName) : "#007bff";
                result.icon = this.createNumberedMarker(index + 1, color);
            }
        } else if (this.fieldMarkerIconImage) {
            result.icon = this.prepareMarkerIcon(record);
        }

        return result;
    }

    /**
     * Create a simple circle marker for unassigned stops.
     */
    createCircleMarker(color) {
        const size = 20;
        const svg = `
            <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" xmlns="http://www.w3.org/2000/svg">
                <circle cx="${size / 2}" cy="${size / 2}" r="${size / 2 - 2}"
                    fill="${color}" stroke="#fff" stroke-width="2"/>
            </svg>
        `;
        return L.divIcon({
            html: svg,
            className: "o_circle_marker",
            iconSize: [size, size],
            iconAnchor: [size / 2, size / 2],
            popupAnchor: [0, -size / 2],
        });
    }

    /**
     * Override to create enhanced popups for tms.order.stop.
     */
    preparePopUpData(record, index) {
        // Use enhanced popup for tms.order.stop
        if (this.resModel === "tms.order.stop") {
            return this.prepareStopPopUpData(record, index);
        }
        // Default popup for other models
        return super.preparePopUpData(record, index);
    }

    /**
     * Create enhanced popup for delivery stops.
     */
    prepareStopPopUpData(record, index) {
        const title = record[this.fieldTitle] || record.display_name || "";
        const address = record[this.fieldAddress] || "";
        const lat = record[this.fieldLatitude];
        const lng = record[this.fieldLongitude];
        const state = record.state || "draft";
        const stateDisplay = record.state_display || state;
        const orderName = record.order_name || "";
        const sequence = record.sequence || index + 1;
        const googleMapsUrl = `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`;
        const stateColor = this.stateColors[state] || this.stateColors.draft;

        let html = `
            <div class='o_stop_popup'>
                <div class='o_popup_header'>
                    <span class="o_stop_number">${sequence}</span>
                    <span class="o_stop_state" style="background-color: ${stateColor}">${this.escapeHtml(stateDisplay)}</span>
                </div>
                <div class='o_map_selector' data-res-id='${record.id}'>
                    <b>${this.escapeHtml(title)}</b>
                </div>
        `;

        if (orderName) {
            html += `<div class="o_popup_order"><i class="fa fa-truck"></i> ${this.escapeHtml(orderName)}</div>`;
        }
        if (address) {
            html += `<div class="o_popup_address"><i class="fa fa-map-marker"></i> ${this.escapeHtml(address)}</div>`;
        }

        const phone = record.partner_phone || record.partner_mobile;
        if (phone) {
            html += `<div class="o_popup_phone"><i class="fa fa-phone"></i> <a href="tel:${phone}">${this.escapeHtml(phone)}</a></div>`;
        }

        const infoParts = [];
        if (record.package_count) infoParts.push(`${record.package_count} pkg`);
        if (record.weight) infoParts.push(`${record.weight.toFixed(1)} kg`);
        if (record.volume) infoParts.push(`${record.volume.toFixed(2)} m³`);
        if (infoParts.length > 0) {
            html += `<div class="o_popup_info"><i class="fa fa-cube"></i> ${infoParts.join(" • ")}</div>`;
        }

        if (record.scheduled_date) {
            const date = new Date(record.scheduled_date);
            const dateStr =
                date.toLocaleDateString() +
                " " +
                date.toLocaleTimeString([], {hour: "2-digit", minute: "2-digit"});
            html += `<div class="o_popup_scheduled"><i class="fa fa-clock-o"></i> ${dateStr}</div>`;
        }

        if (this.enableNavigation) {
            html += `
                <div class="o_popup_actions mt-2">
                    <a href="${googleMapsUrl}" target="_blank" class="btn btn-sm btn-primary">
                        <i class="fa fa-location-arrow"></i> Navigate
                    </a>
                </div>
            `;
        }

        html += `</div>`;
        return html;
    }

    /**
     * Override to use RoutingRenderer for road-based routing.
     * Unassigned stops do not get routing lines.
     */
    async renderRouteLines() {
        if (!this.routingRenderer) {
            return;
        }

        await this.routingRenderer.renderRoutes(this.records, {
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
}
