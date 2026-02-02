/** @odoo-module **/
/*
 * Copyright (C) 2025 KMEE (https://kmee.com.br)
 * @author Luis Felipe Mileo <mileo@kmee.com.br>
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
 */

import {LeafletMapModel} from "@web_view_leaflet_map/leaflet_map_view/leaflet_map_model.esm";

/**
 * TmsStopsMapModel extends LeafletMapModel with TMS-specific resequencing logic.
 *
 * This model overrides the resequence method to use the existing Python method
 * `action_resequence_stops` on the `tms.order.stop` model.
 */
export class TmsStopsMapModel extends LeafletMapModel {
    /**
     * Override to use TMS-specific resequencing method.
     *
     * The existing Python method handles:
     * - Moving stops within the same trip
     * - Moving stops between trips
     * - Renumbering sequences to avoid conflicts
     *
     * @param {Number} recordId - ID of the stop being moved
     * @param {Number} targetGroupId - ID of the target trip (order)
     * @param {Number|null} previousRecordId - ID of the preceding stop (null = first)
     * @returns {Promise<Object>} Result of the operation
     */
    async resequence(recordId, targetGroupId, previousRecordId) {
        if (this.resModel !== "tms.order.stop") {
            return super.resequence(recordId, targetGroupId, previousRecordId);
        }

        if (!targetGroupId) {
            return {success: false, error: "No target order specified"};
        }

        try {
            // Call the Python method with keyword arguments
            // First element of args must be record IDs (empty for classmethod-style call)
            const result = await this.orm.call(
                "tms.order.stop",
                "action_resequence_stops",
                [[]],
                {
                    stop_id: recordId,
                    target_order_id: targetGroupId,
                    ref_stop_id: previousRecordId,
                }
            );

            return result || {success: true};
        } catch (error) {
            return {success: false, error: error.message || "Failed to reorder stop"};
        }
    }
}
