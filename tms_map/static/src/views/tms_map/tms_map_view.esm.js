import {registry} from "@web/core/registry";
import {_t} from "@web/core/l10n/translation";
import {RelationalModel} from "@web/model/relational_model/relational_model";

import {TmsMapArchParser} from "./tms_map_arch_parser.esm";
import {TmsMapViewController} from "./tms_map_controller.esm";
import {TmsMapViewRenderer} from "./tms_map_renderer.esm";

export const tmsMapView = {
    type: "tms_map",
    display_name: _t("Map"),
    icon: "fa fa-map-marker",
    multiRecord: true,
    Controller: TmsMapViewController,
    Renderer: TmsMapViewRenderer,
    ArchParser: TmsMapArchParser,
    Model: RelationalModel,
    searchMenuTypes: ["filter", "favorite"],

    props(genericProps, view) {
        const {arch} = genericProps;
        const archInfo = new view.ArchParser().parse(arch);
        return {
            ...genericProps,
            Model: view.Model,
            Renderer: view.Renderer,
            archInfo,
        };
    },
};

registry.category("views").add("tms_map", tmsMapView);
