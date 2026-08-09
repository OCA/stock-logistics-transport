/** @odoo-module **/
/* Copyright (C) 2026 VSL
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl). */

import {useService} from "@web/core/utils/hooks";
import {registry} from "@web/core/registry";
import {FileUploader} from "@web/views/fields/file_handler";
import {standardWidgetProps} from "@web/views/widgets/standard_widget_props";

import {Component} from "@odoo/owl";

export class TmsDocumentUploader extends Component {
    static template = "tms_document.TmsDocumentUploader";
    static components = {FileUploader};
    static props = {
        ...standardWidgetProps,
        record: {type: Object, optional: true},
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.attachmentIdsToProcess = [];
    }

    async onFileUploaded(file) {
        const attachment = await this.orm.create(
            "ir.attachment",
            [
                {
                    name: file.name,
                    mimetype: file.type,
                    datas: file.data,
                },
            ],
            {context: this._getContext()}
        );
        this.attachmentIdsToProcess.push(attachment);
    }

    async onUploadComplete() {
        try {
            const attachmentIds = [...this.attachmentIdsToProcess];
            const action = await this.orm.call(
                "tms.document",
                "create_document_from_attachment",
                [attachmentIds],
                {context: this._getContext()}
            );
            this.env.services.action.doAction(action);
        } finally {
            this.attachmentIdsToProcess = [];
        }
    }

    _getContext() {
        const holder = this.props.record;
        const context = {};
        if (holder && holder.resModel && holder.resId) {
            context.default_res_model = holder.resModel;
            context.default_res_id = holder.resId;
        }
        return context;
    }
}

export const tmsDocumentUploader = {
    component: TmsDocumentUploader,
};

registry.category("view_widgets").add("tms_document_uploader", tmsDocumentUploader);
