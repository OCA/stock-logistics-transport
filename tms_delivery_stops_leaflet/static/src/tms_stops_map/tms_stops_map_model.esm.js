/** @odoo-module **/
/*
 * Copyright (C) 2026 KMEE (https://kmee.com.br)
 * @author Luis Felipe Mileo <mileo@kmee.com.br>
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
 */

import {LeafletMapModel} from "@web_view_leaflet_map/leaflet_map_view/leaflet_map_model.esm";

/**
 * TmsStopsMapModel extends LeafletMapModel with TMS-specific functionality:
 * - Resequencing stops within and between orders
 * - Moving stops to different orders via drag-and-drop
 */
export class TmsStopsMapModel extends LeafletMapModel {
    /**
     * Resequence a stop within or between orders.
     *
     * @param {Number} recordId - ID of the stop being moved
     * @param {Number|null} targetGroupId - ID of the target order (null = unassigned)
     * @param {Number|null} previousRecordId - ID of the preceding stop
     * @returns {Promise<Object>} Result of the operation
     */
    async resequence(recordId, targetGroupId, previousRecordId) {
        const record = this.data.records.find((r) => r.id === recordId);
        if (!record) {
            return {success: false, error: "Stop not found"};
        }

        // Build updates object
        const updates = {};

        // Calculate new sequence
        if (previousRecordId) {
            const prevRecord = this.data.records.find((r) => r.id === previousRecordId);
            if (prevRecord && prevRecord.sequence !== undefined) {
                updates.sequence = prevRecord.sequence + 1;
            } else {
                updates.sequence = 10;
            }
        } else {
            // Insert at beginning - find minimum sequence in target group
            const targetRecords = this.data.records.filter((r) => {
                const orderId = r.order_id;
                const orderIdValue = Array.isArray(orderId) ? orderId[0] : orderId;
                return orderIdValue === targetGroupId;
            });

            if (targetRecords.length > 0) {
                const minSeq = Math.min(...targetRecords.map((r) => r.sequence || 0));
                updates.sequence = minSeq - 10;
            } else {
                updates.sequence = 10;
            }
        }

        // Update order_id if moving between groups
        const currentOrderId = record.order_id;
        const currentOrderIdValue = Array.isArray(currentOrderId)
            ? currentOrderId[0]
            : currentOrderId;

        if (currentOrderIdValue !== targetGroupId) {
            // Moving to a different order (or to unassigned if targetGroupId is null)
            updates.order_id = targetGroupId || false;
        }

        try {
            await this.orm.write(this.resModel, [recordId], updates);
            return {success: true};
        } catch (error) {
            return {success: false, error: error.message};
        }
    }
}
