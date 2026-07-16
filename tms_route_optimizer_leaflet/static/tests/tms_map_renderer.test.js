/** @odoo-module **/

import {beforeEach, describe, expect, test} from "@odoo/hoot";
import {animationFrame} from "@odoo/hoot-mock";
import {queryAll} from "@odoo/hoot-dom";

import {
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import {RoutingService} from "@web_leaflet_routing/routing_service.esm";

// Mock Leaflet global
function createMockLeaflet() {
    const mockLayer = {
        addTo() {
            return this;
        },
        clearLayers() {
            return undefined;
        },
        getBounds() {
            return {
                isValid: () => true,
                pad: () => this,
            };
        },
        addLayer() {
            return undefined;
        },
        removeLayer() {
            return undefined;
        },
        hasLayer: () => false,
        zoomToShowLayer: (marker, cb) => cb && cb(),
    };

    return {
        map() {
            return {
                setView() {
                    return this;
                },
                addLayer() {
                    return undefined;
                },
                removeLayer() {
                    return undefined;
                },
                fitBounds() {
                    return undefined;
                },
                getZoom: () => 10,
            };
        },
        tileLayer() {
            return {
                addTo() {
                    return this;
                },
            };
        },
        layerGroup() {
            return {...mockLayer};
        },
        markerClusterGroup() {
            return {...mockLayer};
        },
        marker() {
            return {
                bindPopup() {
                    return this;
                },
                on() {
                    return this;
                },
            };
        },
        popup() {
            return {
                setContent() {
                    return this;
                },
            };
        },
        latLng: (lat, lng) => ({lat, lng}),
        polyline(points, opts) {
            return {
                points,
                opts,
                addTo() {
                    return this;
                },
            };
        },
        divIcon(opts) {
            return opts;
        },
        icon(opts) {
            return opts;
        },
    };
}

class TmsOrder extends models.Model {
    _name = "tms.order";

    name = fields.Char();
    map_latitude = fields.Float();
    map_longitude = fields.Float();
    map_display_address = fields.Char();
    route_summary = fields.Char();
    sequence = fields.Integer();

    _records = [
        {
            id: 1,
            name: "Order 1",
            map_latitude: -23.5505,
            map_longitude: -46.6333,
            map_display_address: "São Paulo",
            route_summary: "3 stops",
            sequence: 1,
        },
        {
            id: 2,
            name: "Order 2",
            map_latitude: -22.9068,
            map_longitude: -43.1729,
            map_display_address: "Rio de Janeiro",
            route_summary: "2 stops",
            sequence: 2,
        },
        {
            id: 3,
            name: "Order 3",
            map_latitude: -19.9167,
            map_longitude: -43.9345,
            map_display_address: "Belo Horizonte",
            route_summary: "1 stop",
            sequence: 3,
        },
    ];
}

class ResUsers extends models.Model {
    _name = "res.users";
}

defineModels([TmsOrder, ResUsers]);

describe("TMSMapRenderer", () => {
    let mockL = null;

    beforeEach(() => {
        mockL = createMockLeaflet();
        patchWithCleanup(window, {L: mockL});

        // Mock OSRM routing to return null (fallback path)
        patchWithCleanup(RoutingService.prototype, {
            async getRoute() {
                return null;
            },
        });

        onRpc("res.users", "get_default_leaflet_position", () => {
            return {lat: -23.55, lng: -46.63};
        });
    });

    test("renders with records visible", async () => {
        await mountView({
            type: "leaflet_map",
            resModel: "tms.order",
            arch: `
                <leaflet_map
                    js_class="tms_optimizer_leaflet_map"
                    field_latitude="map_latitude"
                    field_longitude="map_longitude"
                    field_title="name"
                    routing="1"
                >
                    <field name="name" />
                    <field name="map_latitude" />
                    <field name="map_longitude" />
                    <field name="sequence" />
                </leaflet_map>
            `,
        });
        await animationFrame();

        // The map container should exist
        expect(".o_leaflet_map_container").toHaveCount(1);
    });

    test("shows metrics panel when OSRM returns route", async () => {
        patchWithCleanup(RoutingService.prototype, {
            async getRoute() {
                return {
                    geometry: [
                        [-23.5505, -46.6333],
                        [-22.9068, -43.1729],
                    ],
                    distance: 430000,
                    duration: 18000,
                };
            },
        });

        await mountView({
            type: "leaflet_map",
            resModel: "tms.order",
            arch: `
                <leaflet_map
                    js_class="tms_optimizer_leaflet_map"
                    field_latitude="map_latitude"
                    field_longitude="map_longitude"
                    field_title="name"
                    routing="1"
                >
                    <field name="name" />
                    <field name="map_latitude" />
                    <field name="map_longitude" />
                    <field name="sequence" />
                </leaflet_map>
            `,
        });
        await animationFrame();
        await animationFrame();

        const metrics = queryAll(".o_tms_route_metrics");
        expect(metrics.length).toBe(1);
    });

    test("falls back to straight lines when OSRM fails", async () => {
        let polylineCallCount = 0;
        const originalPolyline = mockL.polyline;
        patchWithCleanup(mockL, {
            polyline(...args) {
                polylineCallCount++;
                return originalPolyline(...args);
            },
        });

        await mountView({
            type: "leaflet_map",
            resModel: "tms.order",
            arch: `
                <leaflet_map
                    js_class="tms_optimizer_leaflet_map"
                    field_latitude="map_latitude"
                    field_longitude="map_longitude"
                    field_title="name"
                    routing="1"
                >
                    <field name="name" />
                    <field name="map_latitude" />
                    <field name="map_longitude" />
                    <field name="sequence" />
                </leaflet_map>
            `,
        });
        await animationFrame();
        await animationFrame();

        // Should have drawn at least one polyline (the fallback straight line)
        expect(polylineCallCount).toBeGreaterThan(0);
    });

    test("no metrics panel when no routing", async () => {
        await mountView({
            type: "leaflet_map",
            resModel: "tms.order",
            arch: `
                <leaflet_map
                    js_class="tms_optimizer_leaflet_map"
                    field_latitude="map_latitude"
                    field_longitude="map_longitude"
                    field_title="name"
                >
                    <field name="name" />
                    <field name="map_latitude" />
                    <field name="map_longitude" />
                </leaflet_map>
            `,
        });
        await animationFrame();

        expect(".o_tms_route_metrics").toHaveCount(0);
    });
});
