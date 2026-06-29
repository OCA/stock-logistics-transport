import {SaleOrderLineProductField} from "@sale/js/sale_product_field";
import {x2ManyCommands} from "@web/core/orm_service";
import {useService} from "@web/core/utils/hooks";
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
    setup() {
        super.setup(...arguments);
        this.action = useService("action");
    },

    async _onProductUpdate() {
        await super._onProductUpdate(...arguments);
        if (this.props.record.data.has_trip_product === true) {
            this._openTripConfigurator();
        } else if (this.props.record.data.seat_ticket === true) {
            this._openTicketConfigurator();
        }
    },

    onEditConfiguration() {
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
        } else {
            super.onEditConfiguration(...arguments);
        }
    },

    get hasConfigurationButton() {
        return (
            super.hasConfigurationButton ||
            this.props.record.data.has_trip_product === true ||
            this.props.record.data.tms_scheduled_date_start ||
            this.props.record.data.seat_ticket === true ||
            this.props.record.data.tms_trip_ticket_id
        );
    },

    async _openTripConfigurator() {
        const actionContext = {
            default_product_template_id: this.props.record.data.product_template_id.id,
        };
        if (this.props.record.data.tms_origin_id) {
            actionContext.default_origin = this.props.record.data.tms_origin_id.id;
        }
        if (this.props.record.data.tms_destination_id) {
            actionContext.default_destination =
                this.props.record.data.tms_destination_id.id;
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
            actionContext.default_route = this.props.record.data.tms_route_id.id;
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
        const actionContext = {
            default_product_template_id: this.props.record.data.product_template_id.id,
        };
        if (this.props.record.data.tms_trip_ticket_id) {
            actionContext.default_trip_id =
                this.props.record.data.tms_trip_ticket_id.id;
        }
        if (this.props.record.data.tms_ticket_ids) {
            actionContext.default_ticket_ids =
                this.props.record.data.tms_ticket_ids.currentIds;
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
                    const {tms_trip_ticket_id, tms_ticket_ids} =
                        closeInfo.ticketConfiguration;
                    this.props.record.update({
                        tms_trip_ticket_id,
                        tms_ticket_ids: [x2ManyCommands.set(tms_ticket_ids)],
                    });
                }
            },
        });
    },
});
