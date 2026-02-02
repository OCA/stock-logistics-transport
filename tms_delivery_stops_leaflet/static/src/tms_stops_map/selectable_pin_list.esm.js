/** @odoo-module **/
/*
 * Copyright (C) 2026 KMEE (https://kmee.com.br)
 * @author Luis Felipe Mileo <mileo@kmee.com.br>
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
 */

import {DraggablePinList} from "@web_view_leaflet_map/components/pin-list/draggable_pin_list.esm";
import {useService} from "@web/core/utils/hooks";
import {useState} from "@odoo/owl";

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
}
