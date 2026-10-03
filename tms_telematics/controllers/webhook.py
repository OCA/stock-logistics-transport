# Copyright (C) 2026 Gray Matter Logic (<https://www.graymatterlogic.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json

from odoo import http
from odoo.http import request


class TmsTelematicsHook(http.Controller):
    @http.route(
        "/tms/telematics/hook/<int:account_id>",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def hook(self, account_id):
        account = (
            request.env["tms.telematics.account"].sudo().browse(account_id).exists()
        )
        if not account:
            return request.make_json_response({"error": "unknown"}, status=404)
        try:
            payload = json.loads(request.httprequest.data or b"{}")
        except json.JSONDecodeError:
            return request.make_json_response({"error": "invalid"}, status=400)
        token = request.httprequest.headers.get("X-Telematics-Token")
        body = account._accept_webhook(token, payload)
        status = 200
        if body.get("error") == "forbidden":
            status = 403
        elif body.get("error") == "invalid":
            status = 400
        return request.make_json_response(body, status=status)
