/** @odoo-module **/
/*
 * Copyright (C) 2026 KMEE (https://kmee.com.br)
 * @author Luis Felipe Mileo <mileo@kmee.com.br>
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
 */

import {DraggablePinList} from "@web_view_leaflet_map/components/pin-list/draggable_pin_list.esm";
import {useService} from "@web/core/utils/hooks";
import {onWillUpdateProps, useState} from "@odoo/owl";

/**
 * SelectablePinList extends DraggablePinList with checkbox selection
 * for unassigned stops (group "Sem Viagem" / unassigned group).
 */
export class SelectablePinList extends DraggablePinList {
    static template = "tms_delivery_stops_leaflet.SelectablePinList";

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        // Selection state
        this.selectionState = useState({
            selectedIds: new Set(),
        });

        // Target order state for capacity comparison
        this.targetState = useState({
            orderId: null,
        });

        // Orders capacity data (loaded via ORM)
        this.capacityState = useState({
            orders: {}, // Map of orderId -> capacity data
            loading: false,
        });

        // Load capacity data on mount
        this._loadOrdersCapacity();

        // Reload capacity when props change
        onWillUpdateProps((nextProps) => {
            if (nextProps.records !== this.props.records) {
                this._loadOrdersCapacity(nextProps.records);
            }
        });
    }

    /**
     * Load capacity data for all orders in the records.
     * @param {Array} records - Optional records array (uses props if not provided)
     */
    async _loadOrdersCapacity(records = null) {
        const recordsToUse = records || this.props.records || [];

        // Extract unique order IDs
        const orderIds = new Set();
        for (const record of recordsToUse) {
            const orderId = record[this.props.groupBy || this.props.groupField];
            if (orderId) {
                const id = Array.isArray(orderId) ? orderId[0] : orderId;
                if (id) orderIds.add(id);
            }
        }

        if (orderIds.size === 0) {
            this.capacityState.orders = {};
            return;
        }

        this.capacityState.loading = true;
        try {
            const ordersData = await this.orm.read(
                "tms.order",
                [...orderIds],
                [
                    "name",
                    "weight_capacity",
                    "volume_capacity",
                    "total_weight",
                    "total_volume",
                    "weight_utilization",
                    "volume_utilization",
                    "vehicle_id",
                    "driver_id",
                    "scheduled_date_start",
                ]
            );

            const ordersMap = {};
            for (const order of ordersData) {
                ordersMap[order.id] = {
                    id: order.id,
                    name: order.name,
                    weightCapacity: order.weight_capacity || 0,
                    volumeCapacity: order.volume_capacity || 0,
                    currentWeight: order.total_weight || 0,
                    currentVolume: order.total_volume || 0,
                    weightUtilization: order.weight_utilization || 0,
                    volumeUtilization: order.volume_utilization || 0,
                    vehicleName: this._extractDisplayName(order.vehicle_id),
                    driverName: this._extractDisplayName(order.driver_id),
                    scheduledDate: order.scheduled_date_start
                        ? this._formatDate(order.scheduled_date_start)
                        : "",
                };
            }
            this.capacityState.orders = ordersMap;
        } catch {
            // Silently fail - orders capacity is optional
            this.capacityState.orders = {};
        } finally {
            this.capacityState.loading = false;
        }
    }

    /**
     * Toggle selection of a single record.
     * @param {Event} ev - Click event
     * @param {Number} recordId - Record ID to toggle
     */
    toggleSelection(ev, recordId) {
        ev.stopPropagation();
        const newSet = new Set(this.selectionState.selectedIds);
        if (newSet.has(recordId)) {
            newSet.delete(recordId);
        } else {
            newSet.add(recordId);
        }
        this.selectionState.selectedIds = newSet;
    }

    /**
     * Toggle selection of all records in a group.
     * @param {Event} ev - Click event
     * @param {Object} group - Group object
     */
    toggleSelectAll(ev, group) {
        ev.stopPropagation();
        const newSet = new Set(this.selectionState.selectedIds);
        const groupIds = group.records.map((r) => r.id);
        const allSelected = groupIds.every((id) => newSet.has(id));

        for (const id of groupIds) {
            if (allSelected) {
                newSet.delete(id);
            } else {
                newSet.add(id);
            }
        }
        this.selectionState.selectedIds = newSet;
    }

    /**
     * Check if a record is selected.
     * @param {Number} recordId - Record ID
     * @returns {Boolean}
     */
    isSelected(recordId) {
        return this.selectionState.selectedIds.has(recordId);
    }

    /**
     * Check if all records in a group are selected.
     * @param {Object} group - Group object
     * @returns {Boolean}
     */
    isGroupAllSelected(group) {
        if (group.records.length === 0) return false;
        return group.records.every((r) => this.selectionState.selectedIds.has(r.id));
    }

    /**
     * Get count of selected records.
     * @returns {Number}
     */
    get selectedCount() {
        return this.selectionState.selectedIds.size;
    }

    /**
     * Calculates aggregated statistics from selected stops.
     * @returns {Object} Stats object with totalWeight, totalVolume, stopCount
     */
    get selectionStats() {
        const selectedIds = this.selectionState.selectedIds;
        if (selectedIds.size === 0) {
            return {totalWeight: 0, totalVolume: 0, stopCount: 0};
        }

        const selectedRecords = this.props.records.filter((r) => selectedIds.has(r.id));
        let totalWeight = 0;
        let totalVolume = 0;

        for (const record of selectedRecords) {
            totalWeight += record.weight || 0;
            totalVolume += record.volume || 0;
        }

        return {
            totalWeight: totalWeight.toFixed(2),
            totalVolume: totalVolume.toFixed(3),
            stopCount: selectedRecords.length,
        };
    }

    /**
     * Check if a record is unassigned (no order_id).
     * @param {Object} record - Record object
     * @returns {Boolean}
     */
    isUnassigned(record) {
        const orderId = record[this.props.groupBy || this.props.groupField];
        if (!orderId) return true;
        return Array.isArray(orderId) ? !orderId[0] : !orderId;
    }

    /**
     * Open wizard to create order from selected stops.
     */
    async onCreateOrder() {
        const stopIds = [...this.selectionState.selectedIds];

        if (stopIds.length === 0) {
            this.notification.add("Nenhum stop selecionado.", {type: "warning"});
            return;
        }

        try {
            await this.action.doAction(
                {
                    type: "ir.actions.act_window",
                    name: "Criar Ordem de Entrega",
                    res_model: "tms.order.from.stops",
                    views: [[false, "form"]],
                    target: "new",
                    context: {
                        default_stop_ids: stopIds,
                    },
                },
                {
                    onClose: async () => {
                        // Clear selection and reload data
                        this.selectionState.selectedIds = new Set();
                        if (this.props.onDataReload) {
                            await this.props.onDataReload();
                        }
                    },
                }
            );
        } catch (error) {
            this.notification.add(error.message || "Erro ao abrir wizard", {
                type: "danger",
            });
        }
    }

    /**
     * Clear all selections.
     */
    clearSelection() {
        this.selectionState.selectedIds = new Set();
    }

    // ============================================
    // Capacity Comparison Methods (Phase 1 & 2)
    // ============================================

    /**
     * Get capacity data for a group (order).
     * Calculates totals from stops and utilization if capacity is defined.
     * @param {Object} group - Group object containing records
     * @returns {Object|null} Capacity data or null if not available
     */
    getGroupCapacity(group) {
        if (!group.records || group.records.length === 0) return null;

        // Calculate totals from stops in this group
        let totalWeight = 0;
        let totalVolume = 0;
        for (const record of group.records) {
            totalWeight += record.weight || 0;
            totalVolume += record.volume || 0;
        }

        // Get order ID from first record
        const record = group.records[0];
        const orderId = record[this.props.groupBy || this.props.groupField];
        const id = orderId ? (Array.isArray(orderId) ? orderId[0] : orderId) : null;

        // Get capacity from loaded data (if available)
        const orderData = id ? this.capacityState.orders[id] : null;

        // Calculate utilization percentages
        const weightCapacity = orderData?.weightCapacity || 0;
        const volumeCapacity = orderData?.volumeCapacity || 0;
        const weightUtilization =
            weightCapacity > 0 ? (totalWeight / weightCapacity) * 100 : 0;
        const volumeUtilization =
            volumeCapacity > 0 ? (totalVolume / volumeCapacity) * 100 : 0;

        return {
            totalWeight,
            totalVolume,
            weightCapacity,
            volumeCapacity,
            weightUtilization,
            volumeUtilization,
            hasCapacity: weightCapacity > 0 || volumeCapacity > 0,
        };
    }

    /**
     * Extract display name from a Many2one field (can be array or object).
     * @param {Array|Object|null} field - Many2one field value
     * @returns {String}
     */
    _extractDisplayName(field) {
        if (!field) return "";
        if (Array.isArray(field)) return field[1] || "";
        if (typeof field === "object") return field.display_name || field.name || "";
        return String(field);
    }

    /**
     * Format a date string for display (DD/MM HH:MM).
     * @param {String} dateStr - ISO date string
     * @returns {String} Formatted date
     */
    _formatDate(dateStr) {
        if (!dateStr) return "";
        try {
            const date = new Date(dateStr);
            const day = String(date.getDate()).padStart(2, "0");
            const month = String(date.getMonth() + 1).padStart(2, "0");
            const hours = String(date.getHours()).padStart(2, "0");
            const minutes = String(date.getMinutes()).padStart(2, "0");
            return `${day}/${month} ${hours}:${minutes}`;
        } catch {
            return dateStr;
        }
    }

    /**
     * Get order info (driver/vehicle) for a group.
     * @param {Object} group - Group object
     * @returns {Object|null} Order info with driverName and vehicleName
     */
    getGroupOrderInfo(group) {
        if (!group.records || group.records.length === 0) return null;

        const record = group.records[0];
        const orderId = record[this.props.groupBy || this.props.groupField];
        const id = orderId ? (Array.isArray(orderId) ? orderId[0] : orderId) : null;

        if (!id) return null;
        return this.capacityState.orders[id] || null;
    }

    /**
     * Get order ID for a group.
     * @param {Object} group - Group object
     * @returns {Number|null} Order ID
     */
    getGroupOrderId(group) {
        if (!group.records || group.records.length === 0) return null;

        const record = group.records[0];
        const orderId = record[this.props.groupBy || this.props.groupField];
        return orderId ? (Array.isArray(orderId) ? orderId[0] : orderId) : null;
    }

    /**
     * Navigate to order form view.
     * @param {Event} ev - Click event
     * @param {Object} group - Group object
     */
    async onOrderNameClick(ev, group) {
        ev.stopPropagation();
        ev.preventDefault();

        const orderId = this.getGroupOrderId(group);
        if (!orderId) return;

        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "tms.order",
            res_id: orderId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    /**
     * Get tooltip text for a stop item showing weight and volume.
     * @param {Object} record - Stop record
     * @returns {String} Tooltip text with weight and volume
     */
    getItemTooltip(record) {
        const weight = record.weight || 0;
        const volume = record.volume || 0;
        return `${weight.toFixed(1)} kg | ${volume.toFixed(2)} m³`;
    }

    /**
     * Get the global index of a record across all groups.
     * Returns 1-based index for display.
     * @param {Object} record - The record to find
     * @param {Object} group - The group containing the record
     * @param {Number} recordIndex - The index within the group
     * @returns {Number} Global 1-based index
     */
    getGlobalIndex(record, group, recordIndex) {
        // Calculate offset from previous groups
        let offset = 0;
        for (const g of this.groupedRecords) {
            if (g.name === group.name) {
                break;
            }
            offset += g.records.length;
        }
        return offset + recordIndex + 1;
    }

    /**
     * Get stop type badge label for display.
     * Simple switch by stop_type.
     * @param {Object} record - Stop record
     * @returns {String} Badge label (start, stop, end)
     */
    getStopTypeBadgeLabel(record) {
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
    getStopTypeBadgeClass(record) {
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
     * Check if a stop is an endpoint (origin or destination).
     * @param {Object} record - Stop record
     * @returns {Boolean}
     */
    isEndpoint(record) {
        return record.stop_type === "origin" || record.stop_type === "destination";
    }

    /**
     * Get display name for a stop (partner or location).
     * @param {Object} record - Stop record
     * @returns {String}
     */
    getStopDisplayName(record) {
        if (record.stop_type === "origin" || record.stop_type === "destination") {
            const location = record.location_id;
            if (location) {
                return Array.isArray(location) ? location[1] : location;
            }
        }
        const partner = record.partner_id;
        if (partner) {
            return Array.isArray(partner) ? partner[1] : partner;
        }
        return `Stop #${record.id}`;
    }

    /**
     * Get utilization status class based on percentage.
     * @param {Number} utilization - Percentage value
     * @returns {String} Bootstrap badge class
     */
    getUtilizationClass(utilization) {
        if (utilization > 100) return "bg-danger";
        if (utilization > 80) return "bg-warning text-dark";
        return "bg-success";
    }

    /**
     * Get utilization status text.
     * @param {Number} weightUtil - Weight utilization %
     * @param {Number} volumeUtil - Volume utilization %
     * @returns {String} Status text
     */
    getUtilizationStatus(weightUtil, volumeUtil) {
        const maxUtil = Math.max(weightUtil, volumeUtil);
        if (maxUtil > 100) return "Excedido";
        if (maxUtil > 80) return "Quase cheio";
        return "Disponível";
    }

    /**
     * Get available orders for target selection dropdown.
     * Uses capacity data loaded via ORM.
     * @returns {Array} List of order objects
     */
    get availableOrders() {
        return Object.values(this.capacityState.orders);
    }

    /**
     * Get projected capacity after adding selected stops to target order.
     * @returns {Object|null} Projected capacity data or null
     */
    get projectedCapacity() {
        if (!this.targetState.orderId) return null;

        const targetOrder = this.capacityState.orders[this.targetState.orderId];
        if (!targetOrder) return null;

        const stats = this.selectionStats;
        const addedWeight = parseFloat(stats.totalWeight) || 0;
        const addedVolume = parseFloat(stats.totalVolume) || 0;

        const projectedWeight = targetOrder.currentWeight + addedWeight;
        const projectedVolume = targetOrder.currentVolume + addedVolume;

        const projectedWeightUtil = targetOrder.weightCapacity
            ? (projectedWeight / targetOrder.weightCapacity) * 100
            : 0;
        const projectedVolumeUtil = targetOrder.volumeCapacity
            ? (projectedVolume / targetOrder.volumeCapacity) * 100
            : 0;

        return {
            order: targetOrder,
            addedWeight,
            addedVolume,
            projectedWeight,
            projectedVolume,
            projectedWeightUtil,
            projectedVolumeUtil,
            weightOverflow: projectedWeightUtil > 100,
            volumeOverflow: projectedVolumeUtil > 100,
            hasOverflow: projectedWeightUtil > 100 || projectedVolumeUtil > 100,
        };
    }

    /**
     * Handle target order selection change.
     * @param {Event} ev - Change event from dropdown
     */
    onTargetOrderChange(ev) {
        const value = ev.target.value;
        this.targetState.orderId = value ? parseInt(value, 10) : null;
    }

    /**
     * Clear target order selection.
     */
    clearTargetOrder() {
        this.targetState.orderId = null;
    }
}
