import {SaleOrderLineProductField} from "@sale/js/sale_product_field";
import {x2ManyCommands} from "@web/core/orm_service";
import {useService} from "@web/core/utils/hooks";
import {patch} from "@web/core/utils/patch";

function many2oneId(value) {
    if (!value) {
        return false;
    }
    return value.id || value;
}

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
        const partner = this.props.record.model.root.data.partner_id;
        if (partner) {
            actionContext.default_partner_id = partner.id;
        }
        const lineCard = this.props.record.data.rate_card_id;
        const orderCard = this.props.record.model.root.data.rate_card_id;
        const card = lineCard || orderCard;
        if (card) {
            actionContext.default_rate_card_id = card.id;
        }
        const cargos = this.props.record.data.cargo_ids;
        const cargoRecords = (cargos && cargos.records) || [];
        if (cargoRecords.length) {
            actionContext.cargo_lines_default = cargoRecords.map((row) => ({
                name: row.data.name,
                quantity: row.data.quantity,
                uom_id: many2oneId(row.data.uom_id),
                weight: row.data.weight,
                weight_uom_id: many2oneId(row.data.weight_uom_id),
                volume: row.data.volume,
                volume_uom_id: many2oneId(row.data.volume_uom_id),
                shipment_unit: row.data.shipment_unit,
                container_type: row.data.container_type,
                container_number: row.data.container_number,
                seal_number: row.data.seal_number,
                uld_type: row.data.uld_type,
                uld_number: row.data.uld_number,
            }));
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
                    const tripConfiguration = {
                        ...closeInfo.tripConfiguration,
                    };
                    const cargoLines = tripConfiguration.cargo_lines || [];
                    delete tripConfiguration.cargo_lines;
                    delete tripConfiguration.distance;
                    delete tripConfiguration.distance_uom;
                    const existing =
                        (this.props.record.data.cargo_ids &&
                            this.props.record.data.cargo_ids.records) ||
                        [];
                    const commands = [];
                    cargoLines.forEach((line, index) => {
                        if (!line.name && !line.container_type && !line.uld_type) {
                            return;
                        }
                        const values = {
                            name: line.name,
                            state: "planned",
                            quantity: line.quantity || 1,
                            weight: line.weight || 0,
                            volume: line.volume || 0,
                            shipment_unit: line.shipment_unit,
                            container_type: line.container_type,
                            container_number: line.container_number,
                            seal_number: line.seal_number,
                            uld_type: line.uld_type,
                            uld_number: line.uld_number,
                        };
                        const unit = many2oneId(line.uom_id);
                        const weightUom = many2oneId(line.weight_uom_id);
                        const volumeUom = many2oneId(line.volume_uom_id);
                        if (unit) {
                            values.uom_id = unit;
                        }
                        if (weightUom) {
                            values.weight_uom_id = weightUom;
                        }
                        if (volumeUom) {
                            values.volume_uom_id = volumeUom;
                        }
                        const current = existing[index];
                        commands.push(
                            current
                                ? x2ManyCommands.update(
                                      current.resId || current.id,
                                      values
                                  )
                                : x2ManyCommands.create(false, values)
                        );
                    });
                    existing.slice(cargoLines.length).forEach((row) => {
                        commands.push(
                            x2ManyCommands.delete(row.resId || row.id)
                        );
                    });
                    if (commands.length) {
                        tripConfiguration.cargo_ids = commands;
                    }
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
