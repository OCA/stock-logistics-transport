# Copyright 2022 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
import json

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression


class ShipmentPlanning(models.Model):

    _name = "shipment.planning"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Shipment planning"

    def _default_warehouse_id(self):
        wh = self.env.ref("stock.warehouse0", raise_if_not_found=False)
        return wh.id or False

    name = fields.Char(
        default="/", copy=False, index=True, required=True, readonly=True
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("in_progress", "In progress"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        default="draft",
    )
    warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse",
        ondelete="cascade",
        string="Warehouse",
        required=True,
        states={"draft": [("readonly", False)]},
        readonly=True,
        check_company=True,
        default=lambda r: r._default_warehouse_id(),
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        related="warehouse_id.company_id",
        readonly=True,
        store=True,
        index=True,
    )
    shipment_type = fields.Selection(
        selection=[("outgoing", "Outgoing"), ("incoming", "Incoming")],
        string="Type",
        default="outgoing",
        required=True,
        states={"draft": [("readonly", False)]},
        readonly=True,
        help="Use incoming to plan receptions, use outgoing for deliveries.",
    )
    date_from = fields.Datetime(default=lambda self: self._default_date_from())
    date_to = fields.Datetime(default=lambda self: self._default_date_to())
    picking_to_plan_ids = fields.One2many(
        comodel_name="stock.picking",
        inverse_name="shipment_planning_id",
    )
    picking_to_plan_domain = fields.Char(compute="_compute_picking_to_plan_domain")

    _sql_constraints = [
        (
            "name_uniq",
            "unique(name, company_id)",
            "Reference must be unique per company!",
        ),
    ]

    @api.model
    def _default_date_from(self):
        user_tz = pytz.timezone(self.env.context.get('tz') or 'UTC')
        naive_date = fields.Datetime.now()
        date_from = pytz.utc.localize(naive_date).astimezone(user_tz)
        date_from = date_from.replace(hour=0, minute=0, second=1)
        date_from = date_from.astimezone(pytz.utc).replace(tzinfo=None)
        return date_from

    @api.model
    def _default_date_to(self):
        user_tz = pytz.timezone(self.env.context.get('tz') or 'UTC')
        naive_date = fields.Datetime.now()
        date_to = pytz.utc.localize(naive_date).astimezone(user_tz)
        date_to = date_to.replace(hour=23, minute=59, second=59)
        date_to = date_to.astimezone(pytz.utc).replace(tzinfo=None)
        return date_to

    def action_confirm(self):
        not_draft_shipments = self.filtered(lambda s: s.state != "draft")
        if not_draft_shipments:
            raise UserError(
                _("Following shipment plannings are not in draft:\n %s")
                % "\n".join([s.name for s in not_draft_shipments])
            )
        return self.write({"state": "confirmed"})

    def action_in_progress(self):
        not_confirmed_shipments = self.filtered(lambda s: s.state != "confirmed")
        if not_confirmed_shipments:
            raise UserError(
                _("Following shipment plannings are not confirmed:\n %s")
                % "\n".join([s.name for s in not_confirmed_shipments])
            )
        return self.write({"state": "in_progress"})

    def action_done(self):
        not_in_progress_shipments = self.filtered(lambda s: s.state != "in_progress")
        if not_in_progress_shipments:
            raise UserError(
                _("Following shipment plannings are not in progress:\n %s")
                % "\n".join([s.name for s in not_in_progress_shipments])
            )
        return self.write({"state": "done"})

    def action_cancel(self):
        not_started_shipments = self.filtered(
            lambda s: s.state not in ("confirmed", "in_progress")
        )
        if not_started_shipments:
            raise UserError(
                _("Following shipment plannings are not started:\n %s")
                % "\n".join([s.name for s in not_started_shipments])
            )
        return self.write({"state": "cancel"})

    def action_draft(self):
        not_started_shipments = self.filtered(lambda s: s.state != "cancel")
        if not_started_shipments:
            raise UserError(
                _("Following shipment plannings are not canceled:\n %s")
                % "\n".join([s.name for s in not_started_shipments])
            )
        return self.write({"state": "draft"})

    @api.depends("shipment_type", "warehouse_id", "date_from", "date_to")
    def _compute_picking_to_plan_domain(self):
        for planning in self:
            domain = [
                ("picking_type_code", "=", planning.shipment_type),
                ("location_id", "child_of", planning.warehouse_id.view_location_id.id),
                ("state", "in", ("waiting", "confirmed", "assigned")),
            ]
            if planning.date_from:
                domain = expression.AND(
                    [
                        domain,
                        [
                            (
                                "scheduled_date",
                                ">=",
                                fields.Datetime.to_string(planning.date_from),
                            )
                        ],
                    ]
                )
            if planning.date_to:
                domain = expression.AND(
                    [
                        domain,
                        [
                            (
                                "scheduled_date",
                                "<=",
                                fields.Datetime.to_string(planning.date_to),
                            )
                        ],
                    ]
                )
            planning.picking_to_plan_domain = json.dumps(domain)

    @api.model
    def create(self, vals):
        defaults = self.default_get(["name", "shipment_type"])
        sequence = self.env.ref("shipment_planning.shipment_planning_outgoing_sequence")
        if defaults["shipment_type"] == "incoming":
            sequence = self.env.ref(
                "shipment_planning.shipment_planning_incoming_sequence"
            )
        if vals.get("name", "/") == "/" and defaults.get("name", "/") == "/":
            vals["name"] = sequence.next_by_id()
        return super().create(vals)
