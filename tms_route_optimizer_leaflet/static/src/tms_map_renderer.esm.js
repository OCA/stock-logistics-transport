/** @odoo-module **/

/* global console, L */

import {MapRenderer} from "@web_view_leaflet_map/components/map-component/map_view.esm";
import {registry} from "@web/core/registry";
import {routingService} from "@web_leaflet_routing/routing_service.esm";

/**
 * TMSMapRenderer extends the base MapRenderer with TMS-specific functionality:
 * - Route polylines between stops
 * - Route metrics display (distance, duration)
 * - Optimized stop sequence visualization
 */
export class TMSMapRenderer extends MapRenderer {
    static template = "tms_route_optimizer_leaflet.TMSMapRenderer";

    /**
     * Override setup to add TMS-specific configuration.
     */
    setup() {
        super.setup();

        // TMS-specific state
        this.routePolylines = [];
        this.routeMetrics = {
            totalDistance: 0,
            totalDuration: 0,
        };
    }

    /**
     * Override renderMarkers to also render routes.
     */
    async renderMarkers() {
        await super.renderMarkers();

        // Render routes after markers
        if (this.enableRouting && this.state.records.length > 1) {
            await this.renderRoutes();
        }
    }

    /**
     * Render route polylines between markers.
     */
    async renderRoutes() {
        // Clear existing routes
        this.clearRoutes();

        // Get coordinates from records in order
        const waypoints = this.getOrderedWaypoints();

        if (waypoints.length < 2) {
            return;
        }

        // Get route from OSRM
        const route = await routingService.getRoute(waypoints);

        if (route && route.geometry) {
            // Render the route polyline
            const polyline = this.renderRoute(route.geometry, {
                color: "#007bff",
                weight: 5,
                opacity: 0.7,
            });

            if (polyline) {
                this.routePolylines.push(polyline);
            }

            // Store metrics
            this.routeMetrics = {
                totalDistance: route.distance,
                totalDuration: route.duration,
            };

            // Update metrics display if available
            this.updateMetricsDisplay();
        } else {
            // Fallback: draw straight lines between points
            this.renderStraightLineRoute(waypoints);
        }
    }

    /**
     * Get waypoints from records in proper order.
     * @returns {Array} Array of [lat, lng] coordinate pairs
     */
    getOrderedWaypoints() {
        const waypoints = [];

        // Sort records by sequence if available
        const sortedRecords = [...this.state.records].sort((a, b) => {
            const seqA = a.sequence || 0;
            const seqB = b.sequence || 0;
            return seqA - seqB;
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
     * Render a simple straight-line route between waypoints.
     * @param {Array} waypoints - Array of [lat, lng] pairs
     */
    renderStraightLineRoute(waypoints) {
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

        // Calculate approximate distance
        let totalDistance = 0;
        for (let i = 0; i < waypoints.length - 1; i++) {
            const [lat1, lng1] = waypoints[i];
            const [lat2, lng2] = waypoints[i + 1];
            totalDistance += this.haversineDistance(lat1, lng1, lat2, lng2);
        }

        // Convert km to meters, estimate duration at 1 min/km
        this.routeMetrics = {
            totalDistance: totalDistance * 1000,
            totalDuration: totalDistance * 60,
        };

        this.updateMetricsDisplay();
    }

    /**
     * Calculate Haversine distance between two points.
     * @param {Number} lat1
     * @param {Number} lng1
     * @param {Number} lat2
     * @param {Number} lng2
     * @returns {Number} Distance in kilometers
     */
    haversineDistance(lat1, lng1, lat2, lng2) {
        // Earth's radius in km
        const R = 6371;
        const dLat = this.toRad(lat2 - lat1);
        const dLng = this.toRad(lng2 - lng1);
        const a =
            Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(this.toRad(lat1)) *
                Math.cos(this.toRad(lat2)) *
                Math.sin(dLng / 2) *
                Math.sin(dLng / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return R * c;
    }

    /**
     * Convert degrees to radians.
     * @param {Number} deg
     * @returns {Number}
     */
    toRad(deg) {
        return (deg * Math.PI) / 180;
    }

    /**
     * Update the metrics display element.
     */
    updateMetricsDisplay() {
        // This will be handled by the template/component state
        // For now, just log the metrics
        if (this.routeMetrics.totalDistance > 0) {
            const distanceKm = (this.routeMetrics.totalDistance / 1000).toFixed(1);
            const durationMin = Math.round(this.routeMetrics.totalDuration / 60);
            console.log(`Route: ${distanceKm} km, ${durationMin} min`);
        }
    }

    /**
     * Override clearRoutes to also clear TMS-specific polylines.
     */
    clearRoutes() {
        super.clearRoutes();
        this.routePolylines = [];
        this.routeMetrics = {
            totalDistance: 0,
            totalDuration: 0,
        };
    }

    /**
     * Get formatted distance string.
     * @returns {String}
     */
    get formattedDistance() {
        if (this.routeMetrics.totalDistance > 0) {
            return routingService.formatDistance(this.routeMetrics.totalDistance);
        }
        return "";
    }

    /**
     * Get formatted duration string.
     * @returns {String}
     */
    get formattedDuration() {
        if (this.routeMetrics.totalDuration > 0) {
            return routingService.formatDuration(this.routeMetrics.totalDuration);
        }
        return "";
    }
}

// Register TMS-specific map view
export const tmsMapView = {
    ...registry.category("views").get("leaflet_map"),
    type: "tms_leaflet_map",
    Renderer: TMSMapRenderer,
};

registry.category("views").add("tms_leaflet_map", tmsMapView);
