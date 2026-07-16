/** @odoo-module **/
/*
 * Copyright (C) 2026 KMEE (https://kmee.com.br)
 * @author Luis Felipe Mileo <mileo@kmee.com.br>
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
 *
 * Test helpers for tms_delivery_stops_leaflet module.
 * Provides mock Leaflet API, mock models, fixture data, and view arch.
 */

import {mailModels} from "@mail/../tests/mail_test_helpers";
import {serverState} from "@web/../tests/_framework/mock_server_state.hoot";
import {defineModels, fields, models} from "@web/../tests/web_test_helpers";

// ============================================================================
// Mock Leaflet Factory
// ============================================================================

/**
 * Creates a complete mock of the Leaflet (L) global object.
 * All methods record calls for assertion in tests.
 *
 * @returns {Object} Mock L namespace
 */
export function createMockLeaflet() {
    const calls = {
        mapSetView: [],
        mapFitBounds: [],
        mapAddLayer: [],
        mapRemoveLayer: [],
        markerClusterAddLayer: [],
        markerCreated: [],
        markerOpenPopup: [],
        markerBindPopup: [],
        tileLayerAddTo: [],
        polylineCreated: [],
        layerGroupAddTo: [],
        layerGroupClearLayers: [],
    };

    function createMockBounds(layers) {
        return {
            isValid() {
                return layers.length > 0;
            },
            pad() {
                return this;
            },
            _layers: layers,
        };
    }

    function createMockMarker(latlng) {
        const marker = {
            _latlng: latlng,
            _popup: null,
            _events: {},
            getLatLng() {
                return latlng;
            },
            openPopup() {
                calls.markerOpenPopup.push(latlng);
                return marker;
            },
            bindPopup(popup) {
                marker._popup = popup;
                calls.markerBindPopup.push({latlng, popup});
                return marker;
            },
            on(event, handler) {
                marker._events[event] = handler;
                return marker;
            },
            setIcon() {
                return marker;
            },
        };
        calls.markerCreated.push(marker);
        return marker;
    }

    function createMockMarkerClusterGroup() {
        const layers = [];
        const cluster = {
            _layers: layers,
            addLayer(layer) {
                layers.push(layer);
                calls.markerClusterAddLayer.push(layer);
                return cluster;
            },
            removeLayer(layer) {
                const idx = layers.indexOf(layer);
                if (idx >= 0) layers.splice(idx, 1);
                return cluster;
            },
            getBounds() {
                return createMockBounds(layers);
            },
            hasLayer(layer) {
                return layers.includes(layer);
            },
            zoomToShowLayer(layer, callback) {
                if (callback) callback();
            },
            clearLayers() {
                layers.length = 0;
                return cluster;
            },
        };
        return cluster;
    }

    function createMockMap() {
        const map = {
            _layers: [],
            _view: null,
            _zoom: 12,
            setView(latlng, zoom) {
                map._view = latlng;
                map._zoom = zoom || map._zoom;
                calls.mapSetView.push({latlng, zoom});
                return map;
            },
            fitBounds(bounds) {
                calls.mapFitBounds.push(bounds);
                return map;
            },
            addLayer(layer) {
                map._layers.push(layer);
                calls.mapAddLayer.push(layer);
                return map;
            },
            removeLayer(layer) {
                const idx = map._layers.indexOf(layer);
                if (idx >= 0) map._layers.splice(idx, 1);
                calls.mapRemoveLayer.push(layer);
                return map;
            },
            getZoom() {
                return map._zoom;
            },
            invalidateSize() {
                return map;
            },
            on() {
                return map;
            },
            off() {
                return map;
            },
        };
        return map;
    }

    function createMockPopup() {
        const popup = {
            _content: null,
            setContent(content) {
                popup._content = content;
                return popup;
            },
            setLatLng() {
                return popup;
            },
            openOn() {
                return popup;
            },
        };
        return popup;
    }

    function createMockLayerGroup() {
        const layers = [];
        const group = {
            _layers: layers,
            addTo() {
                calls.layerGroupAddTo.push(group);
                return group;
            },
            addLayer(layer) {
                layers.push(layer);
                return group;
            },
            clearLayers() {
                layers.length = 0;
                calls.layerGroupClearLayers.push(group);
                return group;
            },
            removeLayer(layer) {
                const idx = layers.indexOf(layer);
                if (idx >= 0) layers.splice(idx, 1);
                return group;
            },
        };
        return group;
    }

    const L = {
        _calls: calls,

        map(el, opts) {
            return createMockMap(el, opts);
        },

        markerClusterGroup() {
            return createMockMarkerClusterGroup();
        },

        marker(latlng, opts) {
            return createMockMarker(latlng, opts);
        },

        latLng(lat, lng) {
            return {lat, lng};
        },

        popup() {
            return createMockPopup();
        },

        tileLayer(url, opts) {
            return {
                addTo(map) {
                    calls.tileLayerAddTo.push({url, opts, map});
                    return this;
                },
            };
        },

        layerGroup() {
            return createMockLayerGroup();
        },

        divIcon() {
            return {};
        },

        icon(opts) {
            return opts;
        },

        polyline(latlngs, opts) {
            const polyline = {
                _latlngs: latlngs,
                _opts: opts,
                addTo(layer) {
                    if (layer && layer.addLayer) {
                        layer.addLayer(polyline);
                    }
                    return polyline;
                },
                bindTooltip() {
                    return polyline;
                },
            };
            calls.polylineCreated.push(polyline);
            return polyline;
        },
    };

    return L;
}

// ============================================================================
// Mock Models (TMS-specific only; mail models provide ResPartner, ResUsers)
// ============================================================================

class TmsOrderStop extends models.Model {
    _name = "tms.order.stop";

    order_id = fields.Many2one({relation: "tms.order"});
    stop_type = fields.Selection({
        selection: [
            ["origin", "Origin"],
            ["delivery", "Delivery"],
            ["destination", "Destination"],
        ],
    });
    stop_type_order = fields.Integer();
    sequence = fields.Integer();
    partner_id = fields.Many2one({relation: "res.partner"});
    location_id = fields.Many2one({relation: "res.partner"});
    latitude = fields.Float();
    longitude = fields.Float();
    weight = fields.Float();
    volume = fields.Float();
    display_name = fields.Char();
    display_address = fields.Char();
    state = fields.Selection({
        selection: [
            ["draft", "Draft"],
            ["scheduled", "Scheduled"],
            ["delivered", "Delivered"],
            ["skipped", "Skipped"],
        ],
    });
    scheduled_date = fields.Datetime();

    _records = [
        // === Scenario A: Circular route (order_id=1) ===
        {
            id: 1,
            order_id: 1,
            stop_type: "origin",
            stop_type_order: 0,
            sequence: 1,
            partner_id: false,
            location_id: 10,
            latitude: -23.55,
            longitude: -46.63,
            weight: 0,
            volume: 0,
            display_name: "Depósito Central",
            display_address: "Rua Central, 100",
            state: "scheduled",
        },
        {
            id: 2,
            order_id: 1,
            stop_type: "delivery",
            stop_type_order: 1,
            sequence: 2,
            partner_id: 20,
            location_id: false,
            latitude: -23.56,
            longitude: -46.64,
            weight: 150.5,
            volume: 1.25,
            display_name: "Cliente Alpha",
            display_address: "Av. Alpha, 200",
            state: "scheduled",
        },
        {
            id: 3,
            order_id: 1,
            stop_type: "delivery",
            stop_type_order: 1,
            sequence: 3,
            partner_id: 21,
            location_id: false,
            latitude: -23.57,
            longitude: -46.65,
            weight: 200.0,
            volume: 2.5,
            display_name: "Cliente Beta",
            display_address: "Av. Beta, 300",
            state: "scheduled",
        },
        {
            id: 4,
            order_id: 1,
            stop_type: "destination",
            stop_type_order: 2,
            sequence: 4,
            partner_id: false,
            location_id: 10,
            latitude: -23.55,
            longitude: -46.63,
            weight: 0,
            volume: 0,
            display_name: "Depósito Central",
            display_address: "Rua Central, 100",
            state: "scheduled",
        },
        // === Scenario B: Non-circular route (order_id=2) ===
        {
            id: 5,
            order_id: 2,
            stop_type: "origin",
            stop_type_order: 0,
            sequence: 1,
            partner_id: false,
            location_id: 11,
            latitude: -22.9,
            longitude: -43.17,
            weight: 0,
            volume: 0,
            display_name: "CD Norte",
            display_address: "Rua Norte, 50",
            state: "scheduled",
        },
        {
            id: 6,
            order_id: 2,
            stop_type: "delivery",
            stop_type_order: 1,
            sequence: 2,
            partner_id: 22,
            location_id: false,
            latitude: -22.92,
            longitude: -43.18,
            weight: 75.0,
            volume: 0.5,
            display_name: "Cliente Gamma",
            display_address: "Av. Gamma, 400",
            state: "scheduled",
        },
        {
            id: 7,
            order_id: 2,
            stop_type: "destination",
            stop_type_order: 2,
            sequence: 3,
            partner_id: false,
            location_id: 12,
            latitude: -22.95,
            longitude: -43.2,
            weight: 0,
            volume: 0,
            display_name: "CD Sul",
            display_address: "Rua Sul, 60",
            state: "scheduled",
        },
        // === Scenario C: Unassigned stops (no order_id) ===
        {
            id: 8,
            order_id: false,
            stop_type: "delivery",
            stop_type_order: 1,
            sequence: 1,
            partner_id: 23,
            location_id: false,
            latitude: -23.58,
            longitude: -46.66,
            weight: 50.0,
            volume: 0.75,
            display_name: "Cliente Delta",
            display_address: "Av. Delta, 500",
            state: "draft",
        },
        {
            id: 9,
            order_id: false,
            stop_type: "delivery",
            stop_type_order: 1,
            sequence: 2,
            partner_id: 24,
            location_id: false,
            latitude: -23.59,
            longitude: -46.67,
            weight: 80.0,
            volume: 1.0,
            display_name: "Cliente Epsilon",
            display_address: "Av. Epsilon, 600",
            state: "draft",
        },
    ];
}

class TmsOrder extends models.Model {
    _name = "tms.order";

    name = fields.Char();
    weight_capacity = fields.Float();
    volume_capacity = fields.Float();
    total_weight = fields.Float();
    total_volume = fields.Float();
    weight_utilization = fields.Float();
    volume_utilization = fields.Float();
    vehicle_id = fields.Many2one({relation: "fleet.vehicle"});
    driver_id = fields.Many2one({relation: "res.partner"});
    scheduled_date_start = fields.Datetime();

    _records = [
        {
            id: 1,
            name: "ORD-001",
            weight_capacity: 1000,
            volume_capacity: 10,
            total_weight: 350.5,
            total_volume: 3.75,
            weight_utilization: 35.05,
            volume_utilization: 37.5,
            vehicle_id: 100,
            driver_id: 200,
            scheduled_date_start: "2026-02-10 08:00:00",
        },
        {
            id: 2,
            name: "ORD-002",
            weight_capacity: 500,
            volume_capacity: 5,
            total_weight: 75.0,
            total_volume: 0.5,
            weight_utilization: 15.0,
            volume_utilization: 10.0,
            vehicle_id: 101,
            driver_id: 201,
            scheduled_date_start: "2026-02-10 09:00:00",
        },
    ];
}

class FleetVehicle extends models.Model {
    _name = "fleet.vehicle";

    name = fields.Char();

    _records = [
        {id: 100, name: "Truck 001"},
        {id: 101, name: "Van 002"},
    ];
}

// ============================================================================
// Extend mail's ResPartner to add TMS-specific partner records
// ============================================================================

class TmsResPartner extends mailModels.ResPartner {
    // Must explicitly include serverState records because parent's _records
    // (an instance field) is not accessible via mailModels.ResPartner._records.
    _records = [
        // System records (mirrors web's ResPartner._records)
        ...serverState.companies.map((company) => ({
            id: company.id,
            active: true,
            name: company.name,
        })),
        {
            id: serverState.partnerId,
            active: true,
            name: serverState.partnerName,
        },
        {
            id: serverState.publicPartnerId,
            active: true,
            is_public: true,
            name: serverState.publicPartnerName,
        },
        {
            id: serverState.odoobotId,
            active: false,
            im_status: "bot",
            name: "OdooBot",
        },
        // TMS-specific records
        {id: 10, name: "Depósito Central"},
        {id: 11, name: "CD Norte"},
        {id: 12, name: "CD Sul"},
        {id: 20, name: "Cliente Alpha"},
        {id: 21, name: "Cliente Beta"},
        {id: 22, name: "Cliente Gamma"},
        {id: 23, name: "Cliente Delta"},
        {id: 24, name: "Cliente Epsilon"},
        {id: 200, name: "João"},
        {id: 201, name: "Maria"},
    ];
}

// ============================================================================
// TMS-specific models object (merged with mailModels in setupTmsTests)
// ============================================================================

const tmsModels = {
    TmsOrderStop,
    TmsOrder,
    FleetVehicle,
    ResPartner: TmsResPartner,
};

// ============================================================================
// View Arch
// ============================================================================

export const TMS_STOPS_MAP_ARCH = `
    <leaflet_map
        js_class="tms_stops_leaflet_map"
        field_latitude="latitude"
        field_longitude="longitude"
        field_title="display_name"
        field_address="display_address"
        default_zoom="12"
        show_pin_list="1"
        group_by="order_id"
        group_field="order_id"
        default_order="sequence"
        draggable="1"
        numbered_markers="1"
        routing="1"
        enable_navigation="1"
        unassigned_group_name="Sem Viagem"
        panel_title="Entregas"
        limit="500"
    >
        <field name="id"/>
        <field name="sequence"/>
        <field name="stop_type"/>
        <field name="stop_type_order"/>
        <field name="order_id"/>
        <field name="partner_id"/>
        <field name="location_id"/>
        <field name="latitude"/>
        <field name="longitude"/>
        <field name="display_address"/>
        <field name="scheduled_date"/>
        <field name="state"/>
        <field name="weight"/>
        <field name="volume"/>
    </leaflet_map>
`;

// ============================================================================
// Setup Helper
// ============================================================================

/**
 * Register all mock models for TMS tests.
 * Merges mail models (provides ResPartner, ResUsers, DiscussChannel, etc.)
 * with TMS-specific models (TmsOrderStop, TmsOrder, FleetVehicle).
 * Call this in beforeEach() before mounting views.
 */
export function setupTmsTests() {
    defineModels({...mailModels, ...tmsModels});
}

// Re-export model classes for tests that need direct access
export {TmsOrderStop, TmsOrder, FleetVehicle};
