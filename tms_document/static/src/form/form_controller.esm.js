/** @odoo-module **/
/* Copyright (C) 2026 VSL
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl). */

import {patch} from "@web/core/utils/patch";
import {FormController} from "@web/views/form/form_controller";

patch(FormController.prototype, {
    async onTmsDocumentAdd() {
        const action = await this.orm.call(this.props.resModel, "action_add_document", [
            this.model.root.resId,
        ]);
        this.actionService.doAction(action);
    },
});
