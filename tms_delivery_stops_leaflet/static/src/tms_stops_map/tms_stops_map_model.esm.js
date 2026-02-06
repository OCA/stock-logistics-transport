/** @odoo-module **/
/*
 * Copyright (C) 2026 KMEE (https://kmee.com.br)
 * @author Luis Felipe Mileo <mileo@kmee.com.br>
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
 */

import {_t} from "@web/core/l10n/translation";
import {LeafletMapModel} from "@web_view_leaflet_map/leaflet_map_view/leaflet_map_model.esm";

/**
 * TmsStopsMapModel extends LeafletMapModel with TMS-specific functionality:
 * - Resequencing stops within and between orders
 * - Moving stops to different orders via drag-and-drop
 * - Validation of origin/destination stop constraints
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
            return {success: false, error: _t("Stop not found")};
        }

        // Check if moving between orders
        const currentOrderId = record.order_id;
        const currentOrderIdValue = Array.isArray(currentOrderId)
            ? currentOrderId[0]
            : currentOrderId;
        const isMovingBetweenOrders = currentOrderIdValue !== targetGroupId;

        // Prevent moving origin/destination stops between orders
        // (server constraint _check_unique_endpoint_per_order would reject it)
        if (
            isMovingBetweenOrders &&
            ["origin", "destination"].includes(record.stop_type)
        ) {
            const typeLabel =
                record.stop_type === "origin" ? _t("origin") : _t("destination");
            return {
                success: false,
                error: _t(
                    "Cannot move %s stops between orders. Each order can have only one %s.",
                    typeLabel,
                    typeLabel
                ),
            };
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
        if (isMovingBetweenOrders) {
            updates.order_id = targetGroupId || false;
        }

        try {
            await this.orm.write(this.metaData.resModel, [recordId], updates);
            // Reload data to reflect server-side changes
            this.data = await this._fetchData(this.metaData);
            this.notify();
            return {success: true};
        } catch (error) {
            return {success: false, error: this._extractErrorMessage(error)};
        }
    }
}
