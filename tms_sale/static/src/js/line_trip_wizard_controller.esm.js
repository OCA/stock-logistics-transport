import {formView} from "@web/views/form/form_view";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";

export class TripConfiguratorController extends formView.Controller {
    setup() {
        super.setup();
        this.action = useService("action");
    }

    async onRecordSaved(record) {
        await super.onRecordSaved(...arguments);
        const {
            origin,
            destination,
            start,
            end,
            has_route,
            route,
            distance,
            distance_uom,
            rate_card_id,
        } = record.data;
        const cargoRecords =
            (record.data.cargo_line_ids && record.data.cargo_line_ids.records) || [];
        const cargoLines = cargoRecords.map((row) => ({
            name: row.data.name,
            quantity: row.data.quantity,
            uom_id: row.data.uom_id,
            weight: row.data.weight,
            weight_uom_id: row.data.weight_uom_id,
            volume: row.data.volume,
            volume_uom_id: row.data.volume_uom_id,
            shipment_unit: row.data.shipment_unit || record.data.shipment_unit,
            container_type: row.data.container_type,
            container_number: row.data.container_number,
            seal_number: row.data.seal_number,
            uld_type: row.data.uld_type,
            uld_number: row.data.uld_number,
        }));
        return this.action.doAction({
            type: "ir.actions.act_window_close",
            infos: {
                tripConfiguration: {
                    tms_origin_id: origin,
                    tms_destination_id: destination,
                    tms_scheduled_date_start: start,
                    tms_scheduled_date_end: end,
                    tms_route_flag: has_route,
                    tms_route_id: route,
                    rate_card_id: rate_card_id && (rate_card_id.id || rate_card_id),
                    cargo_lines: cargoLines,
                    distance,
                    distance_uom,
                },
            },
        });
    }
}

registry.category("views").add("sale_order_line_trip_form", {
    ...formView,
    Controller: TripConfiguratorController,
});
