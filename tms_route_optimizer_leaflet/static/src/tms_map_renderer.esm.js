/** @odoo-module **/

/* global L */

import {useState} from "@odoo/owl";

import {registry} from "@web/core/registry";
import {RoutingService} from "@web_leaflet_routing/routing_service.esm";
import {LeafletMapRenderer} from "@web_view_leaflet_map/leaflet_map_view/leaflet_map_renderer.esm";

/**
 * TMSMapRenderer extends the base LeafletMapRenderer with route optimization
 * visualization:
 * - Route polylines between stops (OSRM or straight-line fallback)
 * - Route metrics display (distance, duration, stop count)
 */
export class TMSMapRenderer extends LeafletMapRenderer {
    static template = "tms_route_optimizer_leaflet.TMSMapRenderer";

    setup() {
        super.setup();

        this.routingService = new RoutingService();
        this.routePolylines = [];
        this.routeMetrics = useState({
            totalDistance: 0,
            totalDuration: 0,
            stopCount: 0,
        });
    }

    /**
     * Override renderRouteLines to use OSRM routing when available.
     */
    async renderRouteLines() {
        if (!this.routeLayer) {
            this.routeLayer = L.layerGroup().addTo(this.leafletMap);
        }
        this.routeLayer.clearLayers();
        this.routePolylines = [];

        const waypoints = this._getOrderedWaypoints();
        if (waypoints.length < 2) {
            Object.assign(this.routeMetrics, {
                totalDistance: 0,
                totalDuration: 0,
                stopCount: waypoints.length,
            });
            return;
        }

        // Try OSRM routing
        let route = null;
        try {
            route = await this.routingService.getRoute(waypoints);
        } catch {
            // OSRM unavailable, will use fallback
        }

        if (route && route.geometry) {
            const polyline = L.polyline(route.geometry, {
                color: "#007bff",
                weight: 5,
                opacity: 0.7,
            });
            polyline.addTo(this.routeLayer);
            this.routePolylines.push(polyline);

            Object.assign(this.routeMetrics, {
                totalDistance: route.distance,
                totalDuration: route.duration,
                stopCount: waypoints.length,
            });
        } else {
            // Fallback: draw straight dashed lines
            this._renderStraightLineRoute(waypoints);
        }
    }

    /**
     * Get waypoints from records sorted by sequence.
     * @returns {Array} Array of [lat, lng] pairs
     */
    _getOrderedWaypoints() {
        const waypoints = [];

        const sortedRecords = [...this.records].sort((a, b) => {
            return (a.sequence || 0) - (b.sequence || 0);
        });

        for (const record of sortedRecords) {
            const lat = record[this.fieldLatitude];
            const lng = record[this.fieldLongitude];

            if (this.validateCoordinates(lat, lng)) {
                waypoints.push([lat, lng]);
            }
        }

        return waypoints;
    }

    /**
     * Render straight-line fallback route with distance estimation.
     * @param {Array} waypoints - Array of [lat, lng] pairs
     */
    _renderStraightLineRoute(waypoints) {
        if (!this.routeLayer || waypoints.length < 2) {
            return;
        }

        const polyline = L.polyline(waypoints, {
            color: "#6c757d",
            weight: 3,
            opacity: 0.5,
            dashArray: "10, 10",
        });
        polyline.addTo(this.routeLayer);
        this.routePolylines.push(polyline);

        // Calculate approximate Haversine distance
        let totalDistance = 0;
        for (let i = 0; i < waypoints.length - 1; i++) {
            const [lat1, lng1] = waypoints[i];
            const [lat2, lng2] = waypoints[i + 1];
            totalDistance += this._haversineDistance(lat1, lng1, lat2, lng2);
        }

        // Km → meters for distance, estimate 60 sec/km for duration
        Object.assign(this.routeMetrics, {
            totalDistance: totalDistance * 1000,
            totalDuration: totalDistance * 60,
            stopCount: waypoints.length,
        });
    }

    /**
     * Calculate Haversine distance between two points.
     * @returns {Number} Distance in kilometers
     */
    _haversineDistance(lat1, lng1, lat2, lng2) {
        const R = 6371;
        const dLat = ((lat2 - lat1) * Math.PI) / 180;
        const dLng = ((lng2 - lng1) * Math.PI) / 180;
        const a =
            Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos((lat1 * Math.PI) / 180) *
                Math.cos((lat2 * Math.PI) / 180) *
                Math.sin(dLng / 2) *
                Math.sin(dLng / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return R * c;
    }

    /**
     * Get formatted distance string.
     * @returns {String}
     */
    get formattedDistance() {
        if (this.routeMetrics.totalDistance > 0) {
            return this.routingService.formatDistance(this.routeMetrics.totalDistance);
        }
        return "";
    }

    /**
     * Get formatted duration string.
     * @returns {String}
     */
    get formattedDuration() {
        if (this.routeMetrics.totalDuration > 0) {
            return this.routingService.formatDuration(this.routeMetrics.totalDuration);
        }
        return "";
    }
}

// Register as js_class="tms_optimizer_leaflet_map" for XML views
const leafletMapView = registry.category("views").get("leaflet_map");
registry.category("views").add("tms_optimizer_leaflet_map", {
    ...leafletMapView,
    Renderer: TMSMapRenderer,
});
