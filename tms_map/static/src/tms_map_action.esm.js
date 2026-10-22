import {Component, onWillStart, useState} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";
import {registry} from "@web/core/registry";
import {Layout} from "@web/search/layout";
import {SearchBar} from "@web/search/search_bar/search_bar";
import {WithSearch} from "@web/search/with_search/with_search";
import {TmsUniversalMap} from "./components/tms_map/tms_map.esm";

function xmlText(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;");
}

function filterXml(name, label, domain) {
    return (
        `<filter name="${name}" string="${xmlText(label)}" ` +
        `domain="${xmlText(domain)}"/>`
    );
}

export class TmsMapAction extends Component {
    static template = "tms_map.TmsMapAction";
    static components = {WithSearch, Layout, SearchBar, TmsUniversalMap};
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            model: false,
            arch: "",
            fields: {},
        });
        onWillStart(async () => {
            const model = this.mapMode === "history" ? "tms.order" : "fleet.vehicle";
            const fields = await this.orm.call(model, "fields_get", []);
            this.state.model = model;
            this.state.fields = this.searchFields(model, fields);
            this.state.arch = await this.searchArch(model, fields);
        });
    }

    fieldNames(model, fields) {
        const names = [model === "fleet.vehicle" ? "name" : "vehicle_id"];
        const driver = model === "fleet.vehicle" ? "tms_driver_id" : "driver_id";
        if (fields[driver]) {
            names.push(driver);
        }
        if (fields.tms_vehicle_group_ids) {
            names.push("tms_vehicle_group_ids");
        }
        return names;
    }

    searchFields(model, fields) {
        const picked = {};
        for (const name of this.fieldNames(model, fields)) {
            picked[name] = fields[name];
        }
        return picked;
    }

    get layoutDisplay() {
        return {controlPanel: {layoutActions: true}};
    }

    get mapMode() {
        return this.props.action.context.map_mode || "dispatch";
    }

    get domain() {
        const context = this.props.action.context || {};
        if (this.mapMode === "fleet" && context.active_model === "tms.team") {
            return [["tms_team_id", "=", context.active_id]];
        }
        if (this.mapMode === "history" && context.vehicle_id) {
            return [["vehicle_id", "=", context.vehicle_id]];
        }
        if (
            this.mapMode === "history" &&
            context.active_model === "fleet.vehicle" &&
            context.active_id
        ) {
            return [["vehicle_id", "=", context.active_id]];
        }
        return [];
    }

    async searchArch(model, fields) {
        const vehicle = model === "fleet.vehicle" ? "name" : "vehicle_id";
        const driver = model === "fleet.vehicle" ? "tms_driver_id" : "driver_id";
        const fieldsArch = [`<field name="${vehicle}" string="Vehicle"/>`];
        if (fields[driver]) {
            fieldsArch.push(`<field name="${driver}" string="Driver"/>`);
        }
        if (fields.tms_vehicle_group_ids) {
            fieldsArch.push(
                `<field name="tms_vehicle_group_ids" string="Vehicle Group"/>`
            );
        }
        const filters = await this.filterArch(model, fields, driver);
        return `<search>${fieldsArch.join("")}${filters}</search>`;
    }

    async filterArch(model, fields, driverField) {
        const vehicleField = model === "fleet.vehicle" ? "id" : "vehicle_id";
        const blocks = [];
        if (fields.tms_vehicle_group_ids) {
            const groups = await this.orm.searchRead(
                "tms.vehicle.group",
                [],
                ["name"],
                {order: "name"}
            );
            blocks.push(
                groups.map((group) =>
                    filterXml(
                        `tms_map_group_${group.id}`,
                        group.name,
                        `[('tms_vehicle_group_ids', 'in', ${group.id})]`
                    )
                )
            );
        }
        const vehicleDomain = [["operation", "in", ["cargo", "passenger"]]];
        if (model === "fleet.vehicle") {
            vehicleDomain.unshift(...this.domain);
        }
        const vehicles = await this.orm.searchRead(
            "fleet.vehicle",
            vehicleDomain,
            ["display_name"],
            {order: "name, id"}
        );
        blocks.push(
            vehicles.map((vehicle) =>
                filterXml(
                    `tms_map_vehicle_${vehicle.id}`,
                    vehicle.display_name,
                    `[('${vehicleField}', '=', ${vehicle.id})]`
                )
            )
        );
        if (fields[driverField]) {
            const drivers = await this.orm.searchRead(
                "tms.driver",
                [],
                ["name"],
                {order: "name, id"}
            );
            blocks.push(
                drivers.map((driver) =>
                    filterXml(
                        `tms_map_driver_${driver.id}`,
                        driver.name,
                        `[('${driverField}', '=', ${driver.id})]`
                    )
                )
            );
        }
        return blocks
            .filter((block) => block.length)
            .map((block) => block.join(""))
            .join("<separator/>");
    }
}

registry.category("actions").add("tms_map", TmsMapAction);
