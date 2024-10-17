/** @odoo-module **/

import {SaleOrderLineProductField} from "@sale/js/sale_product_field";
import {patch} from "@web/core/utils/patch";

function formatDateForOdoo(dateString) {
    const date = new Date(dateString);
    const year = date.getFullYear();
    const month = ("0" + (date.getMonth() + 1)).slice(-2);
    const day = ("0" + date.getDate()).slice(-2);
    const hours = ("0" + date.getHours()).slice(-2);
    const minutes = ("0" + date.getMinutes()).slice(-2);
    const seconds = ("0" + date.getSeconds()).slice(-2);
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
}

patch(SaleOrderLineProductField.prototype, {
    async _onProductUpdate() {
        super._onProductUpdate(...arguments);
        if (this.props.record.data.has_trip_product === true) {
            this._openTripConfigurator();
        } else if (this.props.record.data.seat_ticket === true) {
            this._openTicketConfigurator();
        }
    },

    _editLineConfiguration() {
        super._editLineConfiguration(...arguments);
        if (
            this.props.record.data.has_trip_product === true ||
            this.props.record.data.tms_scheduled_date_start
        ) {
            this._openTripConfigurator();
        } else if (
            this.props.record.data.seat_ticket === true ||
            this.props.record.data.tms_trip_ticket_id
        ) {
            this._openTicketConfigurator();
        }
    },

    get isConfigurableLine() {
        return (
            super.isConfigurableLine ||
            this.props.record.data.has_trip_product === true ||
            this.props.record.data.tms_scheduled_date_start ||
            this.props.record.data.seat_ticket === true ||
            this.props.record.data.tms_trip_ticket_id
        );
    },

    async _openTripConfigurator() {
        const actionContext = {
            default_product_template_id: this.props.record.data.product_template_id[0],
        };
        if (this.props.record.data.tms_origin_id) {
            actionContext.default_origin = this.props.record.data.tms_origin_id[0];
        }
        if (this.props.record.data.tms_destination_id) {
            actionContext.default_destination =
                this.props.record.data.tms_destination_id[0];
        }
        if (this.props.record.data.tms_scheduled_date_start) {
            actionContext.default_start = formatDateForOdoo(
                this.props.record.data.tms_scheduled_date_start
            );
        }
        if (this.props.record.data.tms_scheduled_date_end) {
            actionContext.default_end = formatDateForOdoo(
                this.props.record.data.tms_scheduled_date_end
            );
        }
        if (this.props.record.data.tms_route_flag) {
            actionContext.default_has_route = this.props.record.data.tms_route_flag;
        }
        if (this.props.record.data.tms_route_id) {
            actionContext.default_route = this.props.record.data.tms_route_id[0];
        }
        if (this.props.record.resId) {
            actionContext.default_order_line_id = this.props.record.resId;
        }

        this.action.doAction("tms_sale.action_view_trip_sale_order_line", {
            additionalContext: actionContext,
            onClose: async (closeInfo) => {
                if (!closeInfo || closeInfo.special) {
                    // Wizard popup closed or 'Cancel' button triggered
                    if (
                        (!this.props.record.data.tms_origin_id &&
                            !this.props.record.data.tms_route_flag) ||
                        (!this.props.record.data.tms_destination_id &&
                            !this.props.record.data.tms_route_flag) ||
                        !this.props.record.data.tms_scheduled_date_start ||
                        !this.props.record.data.tms_scheduled_date_end ||
                        (!this.props.record.data.tms_route_id &&
                            this.props.record.data.tms_route_flag)
                    ) {
                        // Remove product if trip configuration was cancelled.
                        this.props.record.update({
                            [this.props.name]: undefined,
                        });
                    }
                } else {
                    const tripConfiguration = closeInfo.tripConfiguration;
                    this.props.record.update(tripConfiguration);
                }
            },
        });
    },

    async _openTicketConfigurator() {
        console.log("Data:  ", this.props.record.data);
        console.log("tms_ticket_ids:", typeof this.props.record.data.tms_ticket_ids);
        const actionContext = {
            default_product_template_id: this.props.record.data.product_template_id[0],
        };
        if (this.props.record.data.tms_trip_ticket_id) {
            actionContext.default_trip_id =
                this.props.record.data.tms_trip_ticket_id[0];
        }
        if (this.props.record.data.tms_ticket_ids) {
            actionContext.default_ticket_ids =
                this.props.record.data.tms_ticket_ids._currentIds;
        }
        if (this.props.record.resId) {
            actionContext.default_order_line_id = this.props.record.resId;
        }
        this.action.doAction("tms_sale.action_view_seat_ticket_sale_order_line", {
            additionalContext: actionContext,
            onClose: async (closeInfo) => {
                if (!closeInfo || closeInfo.special) {
                    if (!this.props.record.data.tms_trip_ticket_id) {
                        // Remove product if trip configuration was cancelled.
                        this.props.record.update({
                            [this.props.name]: undefined,
                        });
                    }
                } else {
                    const ticketConfiguration = closeInfo.ticketConfiguration;
                    const ticketIds = ticketConfiguration.tms_ticket_ids;
                    this.props.record.update(ticketConfiguration);
                    this.props.record.data.tms_ticket_ids._currentIds = ticketIds;
                }
            },
        });
    },
});
