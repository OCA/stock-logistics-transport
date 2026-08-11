/** @odoo-module **/
/* Copyright (C) 2026 VSL
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl). */

import {_t} from "@web/core/l10n/translation";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";
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

    get uploadLabel() {
        return _t("Upload");
    }

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.attachmentIdsToProcess = [];
    }

    async onFileUploaded(file) {
        const [attachmentId] = await this.orm.create(
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
        this.attachmentIdsToProcess.push(attachmentId);
    }

    async onUploadComplete() {
        try {
            const attachmentIds = [...this.attachmentIdsToProcess];
            const {count} = await this.orm.call(
                "tms.document",
                "create_document_from_attachment",
                [attachmentIds],
                {context: this._getContext()}
            );
            await this.props.record.load();
            this.notification.add(_t("%(count)s document(s) uploaded", {count}), {
                type: "success",
            });
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

export class TmsDocumentFileReplace extends Component {
    static template = "tms_document.TmsDocumentFileReplace";
    static components = {FileUploader};
    static props = {
        ...standardWidgetProps,
        record: {type: Object, optional: true},
    };

    get replaceFileLabel() {
        return _t("Replace File");
    }

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.attachmentId = false;
    }

    async onFileUploaded(file) {
        const [attachmentId] = await this.orm.create("ir.attachment", [
            {name: file.name, mimetype: file.type, datas: file.data},
        ]);
        this.attachmentId = attachmentId;
    }

    async onUploadComplete() {
        if (!this.attachmentId) {
            return;
        }
        try {
            await this.orm.call("tms.document", "action_replace_file", [
                this.props.record.resId,
                this.attachmentId,
            ]);
            await this.props.record.load();
            this.notification.add(_t("File replaced"), {type: "success"});
        } finally {
            this.attachmentId = false;
        }
    }
}

export const tmsDocumentUploader = {
    component: TmsDocumentUploader,
};

export const tmsDocumentFileReplace = {
    component: TmsDocumentFileReplace,
};

registry.category("view_widgets").add("tms_document_uploader", tmsDocumentUploader);
registry
    .category("view_widgets")
    .add("tms_document_file_replace", tmsDocumentFileReplace);
