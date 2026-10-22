import {Component, useRef, useState} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";
import {Layout} from "@web/search/layout";
import {SearchBar} from "@web/search/search_bar/search_bar";
import {useSearchBarToggler} from "@web/search/search_bar/search_bar_toggler";
import {useSetupAction} from "@web/search/action_hook";
import {useModelWithSampleData} from "@web/model/model";
import {makeActiveField} from "@web/model/relational_model/utils";
import {standardViewProps} from "@web/views/standard_view_props";

export class TmsMapViewController extends Component {
    static template = "tms_map.TmsMapView";
    static components = {Layout, SearchBar};
    static props = {
        ...standardViewProps,
        Model: Function,
        Renderer: Function,
        archInfo: Object,
    };

    setup() {
        this.action = useService("action");
        this.model = useState(
            useModelWithSampleData(this.props.Model, this.modelParams)
        );
        useSetupAction({rootRef: useRef("root")});
        this.searchBarToggler = useSearchBarToggler();
    }

    get modelParams() {
        const {latitude, longitude, mode, motion, shape, perimeter} =
            this.props.archInfo;
        const activeFields = {};
        const names = ["display_name", latitude, longitude];
        if (mode) {
            names.push(mode);
        }
        if (motion) {
            names.push(motion);
        }
        if (shape) {
            names.push(shape);
        }
        if (perimeter) {
            names.push(perimeter);
        }
        for (const name of names) {
            activeFields[name] = makeActiveField();
        }
        const config = this.props.state?.modelState?.config || {
            resModel: this.props.resModel,
            fields: this.props.fields,
            activeFields,
        };
        return {
            config,
            state: this.props.state?.modelState,
            limit: 2000,
        };
    }

    get rendererProps() {
        return {
            model: this.model,
            archInfo: this.props.archInfo,
            onOpen: (resId) => this.action.switchView("form", {resId}),
        };
    }
}
