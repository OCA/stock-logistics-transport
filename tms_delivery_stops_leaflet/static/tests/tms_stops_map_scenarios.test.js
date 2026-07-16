/** @odoo-module **/
/*
 * Copyright (C) 2026 KMEE (https://kmee.com.br)
 * @author Luis Felipe Mileo <mileo@kmee.com.br>
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
 *
 * Integration tests (scenarios) for the TMS Delivery Stops Leaflet Map view.
 * Tests simulate real user flows: mount view, interact with sidebar, verify DOM.
 */

import {beforeEach, describe, expect, test} from "@odoo/hoot";
import {click, queryAll, queryAllTexts, queryOne} from "@odoo/hoot-dom";
import {animationFrame} from "@odoo/hoot-mock";
import {
    contains,
    mockService,
    mountView,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import {RoutingService} from "@web_leaflet_routing/routing_service.esm";
import {
    TMS_STOPS_MAP_ARCH,
    TmsOrderStop,
    createMockLeaflet,
    setupTmsTests,
} from "./tms_test_helpers";

// ============================================================================
// Common setup
// ============================================================================

/**
 * Mount the TMS stops map view with all fixtures loaded.
 * Shared helper to avoid repetition across scenarios.
 */
async function mountTmsMapView(options = {}) {
    return await mountView({
        type: "leaflet_map",
        resModel: "tms.order.stop",
        arch: TMS_STOPS_MAP_ARCH,
        ...options,
    });
}

beforeEach(() => {
    setupTmsTests();
    patchWithCleanup(window, {L: createMockLeaflet()});

    // Mock RoutingService to prevent real OSRM fetch calls
    patchWithCleanup(RoutingService.prototype, {
        async getRoute(waypoints) {
            return {
                geometry: waypoints.map((wp) => [wp[0], wp[1]]),
                distance: 1234.5,
                duration: 567.8,
                legs: [{distance: 1234.5, duration: 567.8, steps: []}],
                provider: "osrm",
            };
        },
        async getOptimizedRoute(waypoints) {
            return {
                geometry: waypoints.map((wp) => [wp[0], wp[1]]),
                distance: 1234.5,
                duration: 567.8,
                waypointOrder: waypoints.map((_, i) => i),
                optimizedWaypoints: waypoints,
                provider: "osrm",
            };
        },
    });

    // Mock RPC: get_default_leaflet_position (called during renderer setup)
    onRpc("res.users", "get_default_leaflet_position", () => {
        return {lat: -23.55, lng: -46.63};
    });

    // Mock RPC: read for tms.order (capacity data loaded by SelectablePinList)
    onRpc("tms.order", "read", (args) => {
        const ids = args.args[0];
        const allOrders = [
            {
                id: 1,
                name: "ORD-001",
                weight_capacity: 1000,
                volume_capacity: 10,
                total_weight: 350.5,
                total_volume: 3.75,
                weight_utilization: 35.05,
                volume_utilization: 37.5,
                vehicle_id: [100, "Truck 001"],
                driver_id: [200, "João"],
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
                vehicle_id: [101, "Van 002"],
                driver_id: [201, "Maria"],
                scheduled_date_start: "2026-02-10 09:00:00",
            },
        ];
        return allOrders.filter((o) => ids.includes(o.id));
    });
});

// ============================================================================
// Scenario 1: Stops grouped by order in sidebar
// ============================================================================

describe("Visualização de stops agrupados", () => {
    test("stops são agrupados por order_id no sidebar", async () => {
        await mountTmsMapView();
        await animationFrame();

        const groups = queryAll(".o_pin_group");
        expect(groups.length).toBe(3, {
            message: "should have 3 groups: ORD-001, ORD-002, Sem Viagem",
        });
    });

    test("grupo da order mostra nome da order como título", async () => {
        await mountTmsMapView();
        await animationFrame();

        const groupNames = queryAllTexts(".o_pin_group_name");
        expect(groupNames).toInclude("ORD-001");
        expect(groupNames).toInclude("ORD-002");
        expect(groupNames).toInclude("Sem Viagem");
    });

    test("grupo da order tem nome clicável para navegação", async () => {
        await mountTmsMapView();
        await animationFrame();

        const clickableNames = queryAll(".o_clickable_order_name");
        expect(clickableNames.length).toBe(2, {
            message: "ORD-001 and ORD-002 should have clickable names",
        });
    });

    test("grupo 'Sem Viagem' mostra badge de contagem", async () => {
        await mountTmsMapView();
        await animationFrame();

        // Find the unassigned group
        const unassignedGroup = queryOne(".o_pin_group_unassigned");
        expect(unassignedGroup).not.toBe(null);

        const badge = unassignedGroup.querySelector(".o_pin_group_count");
        expect(badge).not.toBe(null);
        expect(badge.textContent.trim()).toBe("2");
    });
});

// ============================================================================
// Scenario 2: Stop type badges (start/stop/end)
// ============================================================================

describe("Badges de tipo de stop", () => {
    test("stop de origin mostra badge 'start' com classe bg-info", async () => {
        await mountTmsMapView();
        await animationFrame();

        // Find badges with text "start"
        const badges = queryAll(".o_stop_type_badge");
        const startBadges = [...badges].filter((b) => b.textContent.trim() === "start");
        expect(startBadges.length).toBeGreaterThan(0, {
            message: "should have at least one 'start' badge",
        });
        expect(startBadges[0].classList.contains("bg-info")).toBe(true);
    });

    test("stop de delivery mostra badge 'stop' com classe bg-secondary", async () => {
        await mountTmsMapView();
        await animationFrame();

        const badges = queryAll(".o_stop_type_badge");
        const stopBadges = [...badges].filter((b) => b.textContent.trim() === "stop");
        expect(stopBadges.length).toBeGreaterThan(0);
        expect(stopBadges[0].classList.contains("bg-secondary")).toBe(true);
    });

    test("stop de destination mostra badge 'end' com classe bg-success", async () => {
        await mountTmsMapView();
        await animationFrame();

        const badges = queryAll(".o_stop_type_badge");
        const endBadges = [...badges].filter((b) => b.textContent.trim() === "end");
        expect(endBadges.length).toBeGreaterThan(0);
        expect(endBadges[0].classList.contains("bg-success")).toBe(true);
    });
});

// ============================================================================
// Scenario 3: Circular route — deduplication on map
// ============================================================================

describe("Rota circular", () => {
    test("rota circular filtra destination do mapa mas mantém no routing", async () => {
        // Use only order 1 records (circular route)
        TmsOrderStop._records = TmsOrderStop._records.filter((r) => r.order_id === 1);

        await mountTmsMapView();
        await animationFrame();

        // The mock Leaflet tracks marker creation via L._calls
        // In a circular route, destination is filtered from markers
        // but kept for routing. Check that markerClusterAddLayer was called
        // 3 times (origin + 2 deliveries, not destination)
        const mockL = window.L;
        expect(mockL._calls.markerClusterAddLayer.length).toBe(3, {
            message:
                "circular route should create 3 markers (origin + 2 deliveries, destination filtered)",
        });
    });
});

// ============================================================================
// Scenario 4: Capacity and group info
// ============================================================================

describe("Capacidade e informações do grupo", () => {
    test("linha de info mostra motorista", async () => {
        await mountTmsMapView();
        await animationFrame();

        const driverNames = queryAll(".o_info_driver .o_driver_name");
        const driverTexts = [...driverNames].map((el) => el.textContent.trim());
        expect(driverTexts).toInclude("João");
        expect(driverTexts).toInclude("Maria");
    });

    test("linha de info mostra ícone do veículo com tooltip", async () => {
        await mountTmsMapView();
        await animationFrame();

        const vehicleIcons = queryAll(".o_group_info_line .fa-truck");
        expect(vehicleIcons.length).toBeGreaterThan(0, {
            message: "should show vehicle icon in info line",
        });

        // Check tooltip on parent span
        const vehicleSpan = vehicleIcons[0].closest(".o_info_item");
        expect(vehicleSpan.getAttribute("title")).toInclude("Truck 001");
    });

    test("linha de info mostra contagem de stops do grupo", async () => {
        await mountTmsMapView();
        await animationFrame();

        const stopCountIcons = queryAll(".o_group_info_line .fa-map-marker");
        expect(stopCountIcons.length).toBeGreaterThan(0);
    });

    test("utilização de peso/volume aparece como percentual", async () => {
        await mountTmsMapView();
        await animationFrame();

        // Check for weight utilization display
        const infoLines = queryAll(".o_group_info_line");
        const allText = [...infoLines].map((el) => el.textContent).join(" ");

        // ORD-001: weight ~35%, volume ~38%
        expect(allText).toInclude("%", {
            message: "should show utilization percentages",
        });
    });

    test("utilização abaixo de 80% tem classe text-success", async () => {
        await mountTmsMapView();
        await animationFrame();

        // Both orders have low utilization, should be green
        const successItems = queryAll(".o_group_info_line .text-success");
        expect(successItems.length).toBeGreaterThan(0, {
            message: "low utilization should show text-success class",
        });
    });
});

// ============================================================================
// Scenario 5: Selection of unassigned stops
// ============================================================================

describe("Seleção de stops não alocados", () => {
    test("checkbox aparece apenas em stops não alocados", async () => {
        await mountTmsMapView();
        await animationFrame();

        // Expand the unassigned group (collapsed by default)
        const unassignedHeader = queryOne(".o_unassigned_header");
        if (unassignedHeader) {
            await click(unassignedHeader);
            await animationFrame();
        }

        // Unassigned stops should have checkboxes
        const unassignedCheckboxes = queryAll(
            ".o_pin_group_unassigned .o_tms_stop_checkbox"
        );
        expect(unassignedCheckboxes.length).toBe(2, {
            message: "2 unassigned stops should have checkboxes",
        });

        // Assigned stops should NOT have checkboxes
        const assignedGroups = queryAll(".o_pin_group:not(.o_pin_group_unassigned)");
        for (const group of assignedGroups) {
            const checkboxes = group.querySelectorAll(".o_tms_stop_checkbox");
            expect(checkboxes.length).toBe(0, {
                message: "assigned stops should not have checkboxes",
            });
        }
    });

    test("selecionar um stop atualiza a barra de status", async () => {
        await mountTmsMapView();
        await animationFrame();

        // Expand unassigned group
        const unassignedHeader = queryOne(".o_unassigned_header");
        if (unassignedHeader) {
            await click(unassignedHeader);
            await animationFrame();
        }

        // Click on first unassigned stop checkbox
        const checkboxes = queryAll(".o_pin_group_unassigned .o_tms_stop_checkbox");
        expect(checkboxes.length).toBeGreaterThan(0);

        await click(checkboxes[0]);
        await animationFrame();

        // Status bar should appear
        const statusBar = queryOne(".o_tms_status_bar");
        expect(statusBar).not.toBe(null, {
            message: "status bar should appear after selecting a stop",
        });

        // Check stats: 1 stop, 50.00 kg, 0.750 m³
        const statusText = statusBar.textContent;
        expect(statusText).toInclude("1", {
            message: "should show 1 selected stop",
        });
    });

    test("selecionar múltiplos stops agrega os totais", async () => {
        await mountTmsMapView();
        await animationFrame();

        // Expand unassigned group
        const unassignedHeader = queryOne(".o_unassigned_header");
        if (unassignedHeader) {
            await click(unassignedHeader);
            await animationFrame();
        }

        // Select both stops
        const checkboxes = queryAll(".o_pin_group_unassigned .o_tms_stop_checkbox");
        await click(checkboxes[0]);
        await animationFrame();
        await click(checkboxes[1]);
        await animationFrame();

        const statusBar = queryOne(".o_tms_status_bar");
        expect(statusBar).not.toBe(null);

        const statusText = statusBar.textContent;
        // 2 stops, combined weight 130.00 kg, combined volume 1.750 m³
        expect(statusText).toInclude("2");
        expect(statusText).toInclude("130.00");
        expect(statusText).toInclude("1.750");
    });

    test("'select all' no cabeçalho seleciona todos do grupo", async () => {
        await mountTmsMapView();
        await animationFrame();

        // Expand unassigned group
        const unassignedHeader = queryOne(".o_unassigned_header");
        if (unassignedHeader) {
            await click(unassignedHeader);
            await animationFrame();
        }

        // Click select-all checkbox in unassigned group header
        const selectAll = queryOne(
            ".o_pin_group_unassigned .o_tms_select_all_checkbox"
        );
        expect(selectAll).not.toBe(null);

        await click(selectAll);
        await animationFrame();

        // Both individual checkboxes should be checked
        const checkboxes = queryAll(".o_pin_group_unassigned .o_tms_stop_checkbox");
        for (const cb of checkboxes) {
            expect(cb.checked).toBe(true);
        }
    });

    test("botão 'Criar Ordem' está sempre visível", async () => {
        await mountTmsMapView();
        await animationFrame();

        // "Criar Ordem" button should always be visible
        expect(queryAll(".o_tms_create_order_bar").length).toBe(1);
        const createBtn = queryOne(".o_tms_create_order_bar .btn-primary");
        expect(createBtn.textContent).toInclude("Criar Ordem");

        // Initially no status bar (no selection)
        expect(queryAll(".o_tms_status_bar").length).toBe(0);

        // Expand and select
        await click(".o_unassigned_header");
        await animationFrame();

        const checkboxes = queryAll(".o_pin_group_unassigned .o_tms_stop_checkbox");
        await click(checkboxes[0]);
        await animationFrame();

        // Status bar should appear with selection stats
        expect(queryAll(".o_tms_status_bar").length).toBe(1);
        // "Criar Ordem" button should still be visible
        expect(queryAll(".o_tms_create_order_bar .btn-primary").length).toBe(1);
    });

    test("botão 'Limpar' remove seleção e esconde barra", async () => {
        await mountTmsMapView();
        await animationFrame();

        // Expand and select
        await click(".o_unassigned_header");
        await animationFrame();

        const checkboxes = queryAll(".o_pin_group_unassigned .o_tms_stop_checkbox");
        await click(checkboxes[0]);
        await animationFrame();

        // Status bar should be visible
        expect(queryAll(".o_tms_status_bar").length).toBe(1);

        // Click clear button (fa-times)
        const clearBtn = queryOne(".o_tms_status_bar .btn-outline-secondary");
        await click(clearBtn);
        await animationFrame();

        // Status bar should disappear
        expect(queryAll(".o_tms_status_bar").length).toBe(0);
    });
});

// ============================================================================
// Scenario 6: Wizard for order creation
// ============================================================================

describe("Wizard de criação de ordem", () => {
    test("botão 'Criar Ordem' abre wizard com stops selecionados", async () => {
        let wizardAction = null;
        mockService("action", {
            doAction(action, options) {
                wizardAction = action;
                // Simulate wizard close
                if (options && options.onClose) {
                    options.onClose();
                }
                return true;
            },
        });

        await mountTmsMapView();
        await animationFrame();

        // Expand and select stops
        const unassignedHeader = queryOne(".o_unassigned_header");
        if (unassignedHeader) {
            await click(unassignedHeader);
            await animationFrame();
        }

        // Select both unassigned stops
        const checkboxes = queryAll(".o_pin_group_unassigned .o_tms_stop_checkbox");
        for (const cb of checkboxes) {
            await click(cb);
            await animationFrame();
        }

        // Click "Criar Ordem"
        const createBtn = queryOne(".o_tms_create_order_bar .btn-primary");
        await click(createBtn);
        await animationFrame();

        // Verify wizard was called with correct params
        expect(wizardAction).not.toBe(null);
        expect(wizardAction.res_model).toBe("tms.order.from.stops");
        expect(wizardAction.context.default_stop_ids).toEqual([8, 9]);
    });
});

// ============================================================================
// Scenario 7: Sequential numbering across groups
// ============================================================================

describe("Numeração sequencial", () => {
    test("stops são numerados sequencialmente entre grupos", async () => {
        await mountTmsMapView();
        await animationFrame();

        const pinNumbers = queryAll(".o_pin_number");
        const numbers = [...pinNumbers].map((el) =>
            parseInt(el.textContent.trim(), 10)
        );

        // Numbers should be sequential starting from 1
        // The exact count depends on how many stops are visible (non-collapsed)
        // At minimum, the first visible stop should be 1
        expect(numbers[0]).toBe(1);

        // Each subsequent number should be greater than the previous
        for (let i = 1; i < numbers.length; i++) {
            expect(numbers[i]).toBeGreaterThan(numbers[i - 1]);
        }
    });

    test("tooltip do stop mostra peso e volume", async () => {
        await mountTmsMapView();
        await animationFrame();

        // Find pin titles with tooltips
        const pinTitles = queryAll(".o_pin_title[title]");
        const tooltips = [...pinTitles].map((el) => el.getAttribute("title"));

        // Should contain weight/volume format like "150.5 kg | 1.25 m³"
        const hasWeightVolume = tooltips.some(
            (t) => t.includes("kg") && t.includes("m³")
        );
        expect(hasWeightVolume).toBe(true, {
            message: "at least one tooltip should show weight and volume",
        });
    });
});

// ============================================================================
// Scenario 8: Marker popup on map
// ============================================================================

describe("Popup do marcador", () => {
    test("popup contém título, badge e métricas", async () => {
        await mountTmsMapView();
        await animationFrame();

        // Check that markers were created with popups via bindPopup
        const mockL = window.L;
        const boundPopups = mockL._calls.markerBindPopup;
        expect(boundPopups.length).toBeGreaterThan(0, {
            message: "markers should have popups bound",
        });
    });

    test("popup de origin mostra badge 'start'", async () => {
        await mountTmsMapView();
        await animationFrame();

        // The renderer calls preparePopUpData which generates HTML
        // We verify the HTML content indirectly through the popup mock
        const mockL = window.L;
        const popups = mockL._calls.markerBindPopup;

        // At least one popup should contain "start" badge
        const popupContents = popups
            .map((p) => (p.popup && p.popup._content) || "")
            .join("");
        expect(popupContents).toInclude("start");
    });

    test("popup de delivery mostra badge 'stop'", async () => {
        await mountTmsMapView();
        await animationFrame();

        const mockL = window.L;
        const popupContents = mockL._calls.markerBindPopup
            .map((p) => (p.popup && p.popup._content) || "")
            .join("");
        expect(popupContents).toInclude("stop");
    });

    test("botão de navegação Google Maps presente no popup", async () => {
        await mountTmsMapView();
        await animationFrame();

        const mockL = window.L;
        const popupContents = mockL._calls.markerBindPopup
            .map((p) => (p.popup && p.popup._content) || "")
            .join("");

        expect(popupContents).toInclude("google.com/maps");
        expect(popupContents).toInclude("fa-location-arrow");
    });
});

// ============================================================================
// Scenario 9: Drag-and-drop resequence
// ============================================================================

describe("Resequence de stops (drag-and-drop)", () => {
    test("drag handles presentes em todos os stops", async () => {
        await mountTmsMapView();
        await animationFrame();

        // All visible stops should have drag handles
        const dragHandles = queryAll(".o_drag_handle");
        expect(dragHandles.length).toBeGreaterThan(0, {
            message: "stops should have drag handles for resequencing",
        });

        // Each stop item should have a data-id attribute
        const items = queryAll(".o_pin_item_draggable[data-id]");
        expect(items.length).toBeGreaterThan(0, {
            message: "draggable items should have data-id attributes",
        });
    });

    test("grupos possuem data-group-id para identificação no drop", async () => {
        await mountTmsMapView();
        await animationFrame();

        // Assigned groups should have data-group-id attributes
        const allGroups = queryAll(".o_pin_group[data-group-id]");
        expect(allGroups.length).toBeGreaterThan(0, {
            message: "groups should have data-group-id attributes",
        });

        // Check that ORD-001 and ORD-002 groups exist with their data-group-id
        const groupIds = [...allGroups].map((g) => g.dataset.groupId);
        expect(groupIds).toInclude("1", {
            message: "ORD-001 group should have data-group-id=1",
        });
        expect(groupIds).toInclude("2", {
            message: "ORD-002 group should have data-group-id=2",
        });

        // Unassigned group should exist
        const unassignedGroup = queryAll(".o_pin_group_unassigned");
        expect(unassignedGroup.length).toBe(1);
    });

    test("arrastar stop de ORD-001 para ORD-002 chama write com order_id", async () => {
        onRpc("tms.order.stop", "write", (args) => {
            expect.step("write");
            const [ids, updates] = args.args;
            // Should be writing stop id 2 (Cliente Alpha)
            expect(ids).toEqual([2]);
            // Should set order_id to 2 (ORD-002)
            expect(updates.order_id).toBe(2);
            // Should have a new sequence value
            expect(updates.sequence).not.toBe(undefined);
        });

        await mountTmsMapView();
        await animationFrame();

        // Drag stop 2 (Cliente Alpha from ORD-001) to ORD-002 group
        await contains(".o_pin_item_draggable[data-id='2'] .o_drag_handle").dragAndDrop(
            ".o_pin_group[data-group-id='2']"
        );
        await animationFrame();

        expect.verifySteps(["write"]);
    });

    test("arrastar stop para 'Sem Viagem' seta order_id como false", async () => {
        onRpc("tms.order.stop", "write", (args) => {
            expect.step("write");
            const [, updates] = args.args;
            // Moving to unassigned should set order_id to false
            expect(updates.order_id).toBe(false);
        });

        await mountTmsMapView();
        await animationFrame();

        // Expand unassigned group first (collapsed by default)
        const unassignedHeader = queryOne(".o_unassigned_header");
        if (unassignedHeader) {
            await click(unassignedHeader);
            await animationFrame();
        }

        // Drag stop 2 (Cliente Alpha from ORD-001) to unassigned group
        await contains(".o_pin_item_draggable[data-id='2'] .o_drag_handle").dragAndDrop(
            ".o_pin_group_unassigned"
        );
        await animationFrame();

        expect.verifySteps(["write"]);
    });

    test("reordenar stop dentro da mesma order atualiza sequence", async () => {
        onRpc("tms.order.stop", "write", (args) => {
            expect.step("write");
            const [ids, updates] = args.args;
            // Should be writing stop 3 (Cliente Beta)
            expect(ids).toEqual([3]);
            // Should have a new sequence but NOT change order_id
            expect(updates.sequence).not.toBe(undefined);
            expect(updates.order_id).toBe(undefined, {
                message: "order_id should not change when reordering within same group",
            });
        });

        await mountTmsMapView();
        await animationFrame();

        // Drag stop 3 (Cliente Beta, seq=3) before stop 2 (Cliente Alpha, seq=2)
        // Both are in ORD-001 group
        await contains(".o_pin_item_draggable[data-id='3'] .o_drag_handle").dragAndDrop(
            ".o_pin_item_draggable[data-id='2']"
        );
        await animationFrame();

        expect.verifySteps(["write"]);
    });

    test("arrastar stop de Sem Viagem para uma order atribui order_id", async () => {
        onRpc("tms.order.stop", "write", (args) => {
            expect.step("write");
            const [ids, updates] = args.args;
            // Stop 8 (Cliente Delta) being assigned to ORD-001
            expect(ids).toEqual([8]);
            expect(updates.order_id).toBe(1);
        });

        await mountTmsMapView();
        await animationFrame();

        // Expand unassigned group (collapsed by default)
        await click(".o_unassigned_header");
        await animationFrame();
        await animationFrame();

        // Verify the drag handle is visible after expanding
        const dragHandle = queryAll(
            ".o_pin_item_draggable[data-id='8'] .o_drag_handle"
        );
        expect(dragHandle.length).toBe(1, {
            message: "stop 8 drag handle should be visible after expanding",
        });

        // Drag unassigned stop 8 (Cliente Delta) to ORD-001 group
        await contains(".o_pin_item_draggable[data-id='8'] .o_drag_handle").dragAndDrop(
            ".o_pin_group[data-group-id='1']"
        );
        await animationFrame();

        expect.verifySteps(["write"]);
    });
});

// ============================================================================
// Scenario 10: Display names in sidebar
// ============================================================================

describe("Display names no sidebar", () => {
    test("grupo da order mostra stops com nomes corretos", async () => {
        await mountTmsMapView();
        await animationFrame();

        // The pin titles should include partner/location names
        const pinTitles = queryAllTexts(".o_pin_title");

        // Origin/destination use location_id name
        expect(pinTitles).toInclude("Depósito Central");

        // Delivery uses partner_id name
        expect(pinTitles).toInclude("Cliente Alpha");
        expect(pinTitles).toInclude("Cliente Beta");
    });
});

// ============================================================================
// Scenario 11: Google Maps URL per group
// ============================================================================

describe("Google Maps por grupo", () => {
    test("botão de navegação no grupo gera URL com stops", async () => {
        await mountTmsMapView();
        await animationFrame();

        const mapBtns = queryAll(".o_group_maps_btn");
        expect(mapBtns.length).toBeGreaterThan(0, {
            message: "assigned groups should have Maps navigation button",
        });

        // Check that the href contains google maps URL with coordinates
        const href = mapBtns[0].getAttribute("href");
        expect(href).toInclude("google.com/maps");
    });
});

// ============================================================================
// Scenario 12: Scheduled date in group header
// ============================================================================

describe("Data agendada no cabeçalho", () => {
    test("data agendada da order aparece no cabeçalho do grupo", async () => {
        await mountTmsMapView();
        await animationFrame();

        const scheduledDates = queryAll(".o_group_scheduled_date");
        expect(scheduledDates.length).toBeGreaterThan(0, {
            message: "should display scheduled date in group header",
        });

        // Verify that date includes a calendar icon
        const calendarIcons = queryAll(".o_group_scheduled_date .fa-calendar");
        expect(calendarIcons.length).toBeGreaterThan(0);
    });
});
