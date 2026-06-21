/** @odoo-module **/

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
        const {origin, destination, start, end, has_route, route} = record.data;
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
                },
            },
        });
    }
}

registry.category("views").add("sale_order_line_trip_form", {
    ...formView,
    Controller: TripConfiguratorController,
});
