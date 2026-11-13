# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import json
import logging
from collections import defaultdict
from urllib.parse import urlencode, urlparse, urlunparse

import requests

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .tools import seconds_to_duration

_logger = logging.getLogger("TourSolver Connexion")


class ToursolverTask(models.Model):

    _name = "toursolver.task"
    _description = "Toursolver Task"

    name = fields.Char(readonly=True)
    picking_ids = fields.One2many(
        comodel_name="stock.picking",
        string="Pickings",
        readonly=True,
        inverse_name="toursolver_task_id",
    )
    date = fields.Date(readonly=True, default=fields.Date.context_today)
    task_id = fields.Char(
        "Toursolver task id",
        help="Identifier of the task submitted to the TourSolver service to "
        "optimize the planning/path.",
        readonly=True,
    )
    toursolver_status = fields.Char(
        "TourSolver status",
        help="Status of the optimization task provided by the TourSolver service.",
        readonly=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("in_progress", "In progress"),
            ("aborted", "Aborted"),
            ("error", "Error"),
            ("success", "Success"),
            ("done", "Done"),
            ("cancelled", "Cancelled"),
        ],
        readonly=True,
        store=True,
        compute="_compute_state",
    )
    toursolver_error_message = fields.Text(readonly=True)
    warehouse_id = fields.Many2one(comodel_name="stock.warehouse", readonly=True)
    dock_id = fields.Many2one(comodel_name="stock.dock", readonly=True)
    toursolver_backend_id = fields.Many2one(
        comodel_name="toursolver.backend",
        string="TourSolver Backend",
        default="_get_toursolver_backend",
        readonly=True,
    )
    delivery_resource_ids = fields.Many2many(
        comodel_name="toursolver.resource", string="Delivery resources", readonly=True
    )
    result_data = fields.Binary(attachment=True, readonly=True)
    result_data_filename = fields.Char(readonly=True)
    result_json = fields.Json(compute="_compute_result_json")
    request_data = fields.Binary(readonly=True)
    request_data_filename = fields.Char(readonly=True)
    shipment_advice_ids = fields.One2many(
        comodel_name="shipment.advice",
        inverse_name="toursolver_task_id",
        string="Shipment Advices",
        readonly=True,
    )
    force_delivery_first = fields.Boolean(
        help="Force the delivery to be planned first before other operations. "
        "If set and the shipment contains pickups and deliveries, this "
        "ensures that the deliveries operations are the first ones to be "
        "processed in the resulting plan and other operations follow afterwards.",
        default=False,
    )

    @api.depends("request_data")
    def _compute_result_json(self):
        for record in self:
            val = {}
            if record.request_data:
                val = json.loads(base64.b64decode(record.result_data))
            record.result_json = val

    @api.model_create_multi
    def create(self, vals_list):
        sequence_model = self.env["ir.sequence"]
        for vals in vals_list:
            name = sequence_model.next_by_code("toursolver.task")
            if vals.get("name"):
                name = f"{name} {vals.get('name')}"
            vals["name"] = name
        return super().create(vals_list)

    @api.depends("toursolver_status")
    def _compute_state(self):
        for record in self:
            status = record.toursolver_status
            status = status and status.lower()
            if not status:
                state = "draft"
            elif status in ("error", "failed"):
                state = "error"
            elif status == "aborted":
                state = "cancelled"
            elif status == "terminated":
                state = "success"
            elif status == "done":
                state = "done"
            else:
                state = "in_progress"
            record.state = state

    @api.model
    def _get_default_toursolver_backend(self):
        user_company = self.env.company
        if (
            not user_company.toursolver_backend_id
            or not user_company.toursolver_backend_id.active
        ):
            raise ValidationError(_("There is no active backend for TourSolver."))
        return user_company.toursolver_backend_id

    def _toursolver_query_url(self, action, **url_params):
        backend = self.toursolver_backend_id
        if not backend.url or not backend.api_key:
            raise ValidationError(_("The tousolver backend is not configured."))
        baseurl = backend.url
        url_params = url_params or {}
        url_params["tsCloudApiKey"] = backend.api_key
        url_parts = list(urlparse(baseurl))
        url_parts[2] = url_parts[2] + action
        url_parts[4] = urlencode(url_params)
        return urlunparse(url_parts)

    def _toursolver_post(self, action, json_request):
        self.ensure_one()
        url = self._toursolver_query_url(action)
        response = requests.post(
            url,
            json=json_request,
            headers={"Accept": "application/json"},
            timeout=(
                self.toursolver_backend_id.connection_timeout,
                self.toursolver_backend_id.read_timeout,
            ),
        )
        return self._toursolver_check_response(response)

    def _toursolver_get(self, action, **kwargs):
        self.ensure_one()
        url = self._toursolver_query_url(action, **kwargs)
        response = requests.get(
            url,
            headers={"Accept": "application/json"},
            timeout=(
                self.toursolver_backend_id.connection_timeout,
                self.toursolver_backend_id.read_timeout,
            ),
        )
        return self._toursolver_check_response(response)

    def _toursolver_check_response(self, response):
        """
        Check if the response is OK and process error according.

        Return json content if OK otherwise False
        """
        try:
            self.toursolver_error_message = False
            response.raise_for_status()
        except requests.HTTPError as http_error:
            msg = "\n".join(
                filter(None, [http_error.args[0], response.content.decode()])
            )
            self._toursolver_notify_error(msg)
            return {}
        result = response.json()
        if result["status"] == "ERROR":
            self._toursolver_notify_error(result["message"])
            return {}
        return result

    def _toursolver_notify_error(self, error_msg):
        self.toursolver_error_message = error_msg
        self.toursolver_status = "error"
        _logger.error(error_msg)

    def button_send_request(self):
        for rec in self:
            rec._toursolver_send_request()

    def _toursolver_send_request(self):
        self.ensure_one()
        if self.task_id:
            return True
        json_request = self._toursolver_post_json_request()
        self.request_data = base64.b64encode(json.dumps(json_request).encode())
        self.request_data_filename = f"{self.name} request data.json"
        response = self._toursolver_post(action="optimize", json_request=json_request)
        if response:
            self.toursolver_status = response.get("status")
            self.task_id = response.get("taskId")
        return True

    def _toursolver_post_json_request(self):
        self.ensure_one()
        ret = self._toursolver_json_request_metas()
        ret["depots"] = self._toursolver_json_request_depots()
        ret["orders"] = self._toursolver_json_request_orders()
        ret["resources"] = self._toursolver_json_request_resources()
        ret["options"] = self._toursolver_json_request_options()
        ret["language"] = self.env.user.lang
        ret["simulationName"] = self.name
        return ret

    def _toursolver_json_request_metas(self):
        data = {
            "simulationName": self.name,
            "countryCode": self.env.company.country_id.code,
            "beginDate": self._toursolver_format_date(self.date),
            "language": self.env.user.lang,
        }
        if self.toursolver_backend_id.organization:
            data["organization"] = self.toursolver_backend_id.organization
        return data

    @api.model
    def _toursolver_format_date(self, date):
        return date.strftime("%Y-%m-%d")

    def _toursolver_json_request_depots(self):
        address = self.warehouse_id.partner_id
        return [
            {
                "x": address.partner_longitude,
                "y": address.partner_latitude,
                "id": f"dep_{address.id}",
            }
        ]

    def _toursolver_json_request_orders(self):
        return [
            self._toursolver_json_request_order(
                order_id, partner, operation_type, pickings
            )
            for order_id, (partner, operation_type, pickings) in (
                self._toursolver_order_groups().items()
            )
        ]

    def _toursolver_order_groups(self):
        """Return order groups for the TourSolver request.

        In toursolver we group orders by partner and operation type (pickup or delivery).
        """
        self.ensure_one()
        groups = {}
        operation_types = {"incoming": "pickup", "outgoing": "delivery"}
        for picking in self.picking_ids.filtered("partner_id"):
            operation_type = operation_types.get(picking.picking_type_id.code)
            if not operation_type:
                raise ValidationError(
                    _(
                        "Picking %(picking)s has an unsupported operation type "
                        "%(operation_type)s for TourSolver."
                    )
                    % {
                        "picking": picking.display_name,
                        "operation_type": picking.picking_type_id.code,
                    }
                )
            order_id = f"{picking.partner_id.id}_{operation_type}"
            if order_id not in groups:
                groups[order_id] = (
                    picking.partner_id,
                    operation_type,
                    self.env["stock.picking"],
                )
            groups[order_id] = (
                groups[order_id][0],
                groups[order_id][1],
                groups[order_id][2] | picking,
            )
        return groups

    def _toursolver_json_request_order(
        self, order_id, partner, operation_type, pickings
    ):
        backend = self.toursolver_backend_id
        order = self._toursolver_json_request_order_common(
            order_id, partner, operation_type
        )
        custom_data_map = self._toursolver_json_request_order_custom_data_map(
            partner, pickings
        )
        if custom_data_map:
            order["customDataMap"] = custom_data_map
        if not backend.delivery_window_disabled:
            time_windows = self._toursolver_json_request_order_time_window(partner)
            if time_windows:
                order["timeWindows"] = time_windows
        return order

    def _get_toursolveroperation_type(self, operation_type):
        if operation_type == "pickup":
            return 1
        if self.force_delivery_first:
            return 2
        return 0

    def _toursolver_json_request_order_common(self, order_id, partner, operation_type):
        self.ensure_one()
        backend = self.toursolver_backend_id
        phones = filter(None, (partner.mobile or None, partner.phone or None))
        delivery_duration = backend._get_partner_delivery_duration(partner)
        order_type = self._get_toursolveroperation_type(operation_type)
        data = {
            "customerId": partner.ref,
            "fixedVisitDuration": seconds_to_duration(delivery_duration),
            "id": order_id,
            "label": partner.display_name,
            "phone": "| ".join(phones),
            "type": order_type,
            "x": partner.partner_longitude,
            "y": partner.partner_latitude,
            "possibleVisitDays": ["1"],
        }
        order_properties = backend._get_rqst_orders_properties()
        if order_properties:
            data.update(order_properties)
        data.update({"id": order_id, "type": order_type})
        return data

    @api.model
    def _toursolver_json_request_order_custom_data_map(self, partner, pickings):
        custom_data_map = {}
        if partner.comment:
            custom_data_map["notes"] = partner.comment
        if not all(
            char == "" or char.isspace() for char in partner.contact_address.split("\n")
        ):
            custom_data_map["address"] = partner.contact_address
        custom_data_map["pickingIds"] = json.dumps(pickings.ids)
        return custom_data_map

    @api.model
    def _toursolver_json_request_order_time_window(self, partner):
        delivery_windows = partner._get_delivery_windows(
            str(fields.Date.from_string(self.date).weekday())
        )
        time_windows = []
        if delivery_windows:
            for window in delivery_windows:
                time_windows.append(
                    {
                        "beginTime": window.float_to_time_repr(
                            window.time_window_start
                        ),
                        "endTime": window.float_to_time_repr(window.time_window_end),
                    }
                )
        else:
            default_window = self._toursolver_default_delivery_window()
            if default_window:
                time_windows.append(default_window)
        return time_windows

    def _toursolver_default_delivery_window(self):
        self.ensure_one()
        delivery_window_model = self.env["toursolver.delivery.window"]
        backend = self.toursolver_backend_id
        if (
            not backend.partner_default_delivery_window_start
            or not backend.partner_default_delivery_window_end
        ):
            return None
        return {
            "beginTime": delivery_window_model.float_to_time_repr(
                backend.partner_default_delivery_window_start
            ),
            "endTime": delivery_window_model.float_to_time_repr(
                backend.partner_default_delivery_window_end
            ),
        }

    def _toursolver_json_request_resources(self):
        return [
            self._toursolver_json_request_resource(resource)
            for resource in self.delivery_resource_ids
        ]

    def _toursolver_json_request_resource(self, resource):
        res = resource._get_resource_properties()
        res.update(self._toursolver_json_request_resource_start_end_position(resource))
        return res

    def _toursolver_json_request_resource_start_end_position(self, resource):
        address = self.warehouse_id.partner_id
        res = {
            "startX": address.partner_longitude,
            "startY": address.partner_latitude,
            "endX": address.partner_longitude,
            "endY": address.partner_latitude,
        }
        if resource.use_delivery_person_coordinates_as_end and resource.partner_id:
            res.update(
                {
                    "endX": resource.partner_id.partner_longitude,
                    "endY": resource.partner_id.partner_latitude,
                }
            )
        return res

    def _toursolver_json_request_options(self):
        self.ensure_one()
        res = self.toursolver_backend_id._get_rqst_options_properties()
        res.update(
            {
                "maxOptimDuration": seconds_to_duration(
                    self.toursolver_backend_id.duration
                )
            }
        )
        return res

    def button_check_status(self):
        for rec in self:
            rec._toursolver_check_status()

    def _toursolver_check_status(self):
        self.ensure_one()
        result = self._toursolver_get(action="status", taskId=self.task_id)
        if not result:
            return
        self.toursolver_status = result["optimizeStatus"]
        if self.state == "error" and result.get("message"):
            self.toursolver_error_message = result["message"]

    def button_get_result(self):
        for rec in self:
            rec._toursolver_get_result()

    def _toursolver_get_result(self):
        self.ensure_one()
        result = self._toursolver_get(action="toursResult", taskId=self.task_id)
        if not result:
            return
        self.result_data = base64.b64encode(json.dumps(result).encode())
        self.result_data_filename = f"{self.name} result data.json"
        self._toursolver_validate_result()
        if not self.shipment_advice_ids and self.state in ("success", "done"):
            self._toursolver_create_shipment_advices()
        self._toursolver_sort_planned_picking()
        if self.state == "success":
            self.toursolver_status = "done"

    def _toursolver_validate_result(self):
        self.ensure_one()
        order_groups = self._toursolver_order_groups()
        expected_order_ids = set(order_groups)
        received_order_ids = self._toursolver_planned_order_ids()
        missing_order_ids = expected_order_ids - received_order_ids
        unexpected_order_ids = received_order_ids - expected_order_ids
        error_messages = []
        if missing_order_ids:
            missing_orders = [
                _("%(partner)s (%(operation)s)")
                % {
                    "partner": order_groups[order_id][0].display_name,
                    "operation": order_groups[order_id][1],
                }
                for order_id in sorted(missing_order_ids)
            ]
            error_messages.append(
                _(
                    "The following operations are not found into the "
                    "optimization result: %s"
                )
                % ", ".join(missing_orders)
            )
        if unexpected_order_ids:
            error_messages.append(
                _(
                    "The following order ids are not expected into the "
                    "optimization result: %(names)s"
                )
                % {"names": ", ".join(str(i) for i in sorted(unexpected_order_ids))}
            )
        if error_messages:
            self.write(
                {
                    "toursolver_status": "failed",
                    "toursolver_error_message": "\n".join(error_messages),
                }
            )

    def _toursolver_planned_order_ids_by_resource_id(self):
        result = defaultdict(list)
        for tour in self.result_json["tours"]:
            for order in tour["plannedOrders"]:
                if (
                    order.get("resourceId")
                    and order.get("stopId")
                    and order.get("stopType", 0) == 0
                ):
                    result[order.get("resourceId")].append(str(order.get("stopId")))
        return result

    def _toursolver_planned_order_ids(self):
        planned_order_ids_by_resource = (
            self._toursolver_planned_order_ids_by_resource_id()
        )
        res = []
        for order_ids in planned_order_ids_by_resource.values():
            res.extend(order_ids)
        return set(res)

    def _toursolver_pickings_to_plan_by_resource(self):
        order_groups = self._toursolver_order_groups()
        for (
            resource_id,
            order_ids,
        ) in self._toursolver_planned_order_ids_by_resource_id().items():
            resource = self.delivery_resource_ids.filtered(
                lambda r, r_id=resource_id: r.resource_id == r_id
            )
            pickings_to_plan = self.env["stock.picking"]
            for order_id in order_ids:
                if order_id in order_groups:
                    pickings_to_plan |= order_groups[order_id][2]
            yield resource, pickings_to_plan

    def _toursolver_new_shipment_advice_planer(self, resource, pickings_to_plan):
        planner = self.env["shipment.advice.planner"].new({})
        planner.warehouse_id = self.warehouse_id
        planner.shipment_planning_method = "simple"
        planner.picking_to_plan_ids = pickings_to_plan
        planner.toursolver_resource_id = resource
        planner.toursolver_task_id = self
        planner.dock_id = self.dock_id
        return planner

    def _toursolver_create_shipment_advices(self):
        self.ensure_one()
        for (
            resource,
            pickings_to_plan,
        ) in self._toursolver_pickings_to_plan_by_resource():
            planner = self._toursolver_new_shipment_advice_planer(
                resource, pickings_to_plan
            )
            planner._plan_shipments_for_method()

    def button_show_shipment_advice(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Shipment Advice"),
            "view_mode": "calendar,tree,form",
            "res_model": self.shipment_advice_ids._name,
            "domain": [("toursolver_task_id", "=", self.id)],
            "context": self.env.context,
        }

    @api.model
    def _cron_sync_task(self):
        for task in self.search([("state", "=", "in_progress")]):
            task.button_check_status()
        for task in self.search([("state", "=", "success")]):
            task.button_get_result()
        for task in self.search([("state", "=", "draft")]):
            task.button_send_request()

    def _toursolver_sort_planned_picking(self):
        self.ensure_one()
        for shipment in self.shipment_advice_ids:
            if not shipment.toursolver_resource_id:
                continue
            order_groups = self._toursolver_order_groups()
            for rank, order_id in enumerate(
                self._toursolver_planned_order_ids_sorted(
                    shipment.toursolver_resource_id.resource_id
                ),
                start=1,
            ):
                if order_id not in order_groups:
                    continue
                partner, operation_type, _pickings = order_groups[order_id]
                planned = shipment.planned_partner_order_ids.filtered(
                    lambda plo, p=partner, o=operation_type: plo.partner_id == p
                    and plo.operation_type == o
                )
                planned.write({"sequence": rank})

    def _toursolver_planned_order_ids_sorted(self, resource_id):
        for tour in self.result_json["tours"]:
            for order in tour["plannedOrders"]:
                if (
                    order.get("resourceId") == resource_id
                    and order.get("stopId")
                    and order.get("stopType", 0) == 0
                ):
                    yield str(order.get("stopId"))

    def button_cancel(self):
        self.write({"toursolver_status": "aborted"})
