# Copyright 2021 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ShipmentAdvice(models.Model):
    _name = "shipment.advice"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Shipment Advice"
    _order = "arrival_date asc, id desc"

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
        default=_default_warehouse_id,
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
    dock_id = fields.Many2one(
        comodel_name="stock.dock",
        ondelete="restrict",
        string="Loading dock",
        states={"draft": [("readonly", False)], "confirmed": [("readonly", False)]},
        readonly=True,
        index=True,
    )
    arrival_date = fields.Datetime(
        string="Arrival date",
        states={"draft": [("readonly", False)], "confirmed": [("readonly", False)]},
        readonly=True,
        help=(
            "When will the shipment arrive at the (un)loading dock. It is a "
            "planned date until in progress, then it represents the real one."
        ),
    )
    departure_date = fields.Datetime(
        string="Departure date",
        states={
            "draft": [("readonly", False)],
            "confirmed": [("readonly", False)],
            "in_progress": [("readonly", False)],
        },
        readonly=True,
        help=(
            "When will the shipment leave the (un)loading dock. It is a "
            "planned date until in progress, then it represents the real one."
        ),
    )
    ref = fields.Char(
        string="Consignment/Truck Ref.",
        states={
            "draft": [("readonly", False)],
            "confirmed": [("readonly", False)],
            "in_progress": [("readonly", False)],
        },
        readonly=True,
    )
    total_load = fields.Float(
        string="Total load (kg)", digits=(16, 2), compute="_compute_total_load",
    )
    planned_move_ids = fields.One2many(
        comodel_name="stock.move",
        inverse_name="shipment_advice_id",
        string="Planned content list",
        states={
            "draft": [("readonly", False)],
            "confirmed": [("readonly", False)],
            "in_progress": [("readonly", False)],
        },
        readonly=True,
    )
    planned_moves_count = fields.Integer(compute="_compute_count")
    planned_picking_ids = fields.One2many(
        comodel_name="stock.picking",
        compute="_compute_picking_ids",
        string="Planned transfers",
    )
    planned_pickings_count = fields.Integer(compute="_compute_count")
    loaded_move_line_ids = fields.One2many(
        comodel_name="stock.move.line",
        inverse_name="shipment_advice_id",
        string="Loaded content list",
        states={
            "draft": [("readonly", False)],
            "confirmed": [("readonly", False)],
            "in_progress": [("readonly", False)],
        },
        readonly=True,
    )
    loaded_move_line_without_package_ids = fields.One2many(
        comodel_name="stock.move.line",
        inverse_name="shipment_advice_id",
        string="Loaded content list (w/o packages)",
        states={
            "draft": [("readonly", False)],
            "confirmed": [("readonly", False)],
            "in_progress": [("readonly", False)],
        },
        domain=[("package_level_id", "=", False)],
        readonly=True,
    )
    loaded_move_lines_without_package_count = fields.Integer(compute="_compute_count")
    loaded_picking_ids = fields.One2many(
        comodel_name="stock.picking",
        compute="_compute_picking_ids",
        string="Loaded transfers",
    )
    loaded_pickings_count = fields.Integer(compute="_compute_count")
    loaded_package_ids = fields.One2many(
        comodel_name="stock.quant.package",
        compute="_compute_package_ids",
        string="Packages",
    )
    loaded_package_level_ids = fields.One2many(
        comodel_name="stock.package_level",
        compute="_compute_package_ids",
        string="Package Levels",
    )
    loaded_packages_count = fields.Integer(compute="_compute_count")
    carrier_ids = fields.Many2many(
        comodel_name="delivery.carrier",
        string="Related shipping methods",
        compute="_compute_carrier_ids",
        help=(
            "Concerned shipping method  for this shipment advice. It can be "
            "used to determine what are the eligible deliveries to load in "
            "the shipment when you don't have planned content "
            "(e.g. through the shopfloor application)."
        ),
    )

    _sql_constraints = [
        (
            "name_uniq",
            "unique(name, company_id)",
            "Reference must be unique per company!",
        ),
    ]

    @api.depends("loaded_move_line_ids.result_package_id.shipping_weight")
    def _compute_total_load(self):
        for shipment in self:
            packages = shipment.loaded_move_line_ids.result_package_id
            shipment.total_load = sum(packages.mapped("shipping_weight"))

    @api.depends("planned_move_ids", "loaded_move_line_ids")
    def _compute_picking_ids(self):
        for shipment in self:
            shipment.planned_picking_ids = shipment.planned_move_ids.picking_id
            shipment.loaded_picking_ids = shipment.loaded_move_line_ids.picking_id

    @api.depends("loaded_move_line_ids.package_level_id.package_id",)
    def _compute_package_ids(self):
        for shipment in self:
            shipment.loaded_package_level_ids = (
                shipment.loaded_move_line_ids.package_level_id
            )
            package_ids = set()
            for line in shipment.loaded_move_line_ids:
                if line.package_level_id:
                    package_ids.add(line.package_level_id.package_id.id)
            shipment.loaded_package_ids = self.env["stock.quant.package"].browse(
                package_ids
            )

    @api.depends("planned_picking_ids", "planned_move_ids")
    def _compute_count(self):
        for shipment in self:
            shipment.planned_pickings_count = len(shipment.planned_picking_ids)
            shipment.planned_moves_count = len(shipment.planned_move_ids)
            shipment.loaded_pickings_count = len(shipment.loaded_picking_ids)
            shipment.loaded_move_lines_without_package_count = len(
                shipment.loaded_move_line_without_package_ids
            )
            shipment.loaded_packages_count = len(shipment.loaded_package_ids)

    @api.depends("planned_picking_ids", "loaded_picking_ids")
    def _compute_carrier_ids(self):
        for shipment in self:
            if shipment.planned_picking_ids:
                shipment.carrier_ids = shipment.planned_picking_ids.carrier_id
            else:
                shipment.carrier_ids = shipment.loaded_picking_ids.carrier_id

    @api.model
    def create(self, vals):
        defaults = self.default_get(["name", "shipment_type"])
        sequence = self.env.ref("shipment_advice.shipment_advice_outgoing_sequence")
        if defaults["shipment_type"] == "incoming":
            sequence = self.env.ref("shipment_advice.shipment_advice_incoming_sequence")
        if vals.get("name", "/") == "/" and defaults.get("name", "/") == "/":
            vals["name"] = sequence.next_by_id()
        return super().create(vals)

    def action_confirm(self):
        for shipment in self:
            if shipment.state != "draft":
                raise UserError(
                    _("Shipment {} is not draft, operation aborted.").format(
                        shipment.name
                    )
                )
            if not shipment.arrival_date:
                raise UserError(
                    _("Arrival date should be set on the shipment advice {}.").format(
                        shipment.name
                    )
                )
            shipment.state = "confirmed"
        return True

    def action_in_progress(self):
        for shipment in self:
            if shipment.state != "confirmed":
                raise UserError(
                    _("Shipment {} is not confirmed, operation aborted.").format(
                        shipment.name
                    )
                )
            if not shipment.dock_id:
                raise UserError(
                    _("Dock should be set on the shipment advice {}.").format(
                        shipment.name
                    )
                )
            shipment.arrival_date = fields.Datetime.now()
            shipment.state = "in_progress"
        return True

    def action_done(self):
        wiz_model = self.env["stock.backorder.confirmation"]
        for shipment in self:
            if shipment.state != "in_progress":
                raise UserError(
                    _("Shipment {} is not started, operation aborted.").format(
                        shipment.name
                    )
                )
            # Validate transfers (create backorders for unprocessed lines)
            if shipment.shipment_type == "incoming":
                for picking in self.planned_picking_ids:
                    if picking.state in ("cancel", "done"):
                        continue
                    if picking._check_backorder():
                        wiz = wiz_model.create({})
                        wiz.pick_ids = picking
                        wiz.process()
                    else:
                        picking.action_done()
            else:
                backorder_policy = (
                    shipment.company_id.shipment_advice_outgoing_backorder_policy
                )
                if backorder_policy == "create_backorder":
                    for picking in self.loaded_picking_ids:
                        if picking._check_backorder():
                            wiz = wiz_model.create({})
                            wiz.pick_ids = picking
                            wiz.process()
                        else:
                            picking.action_done()
                else:
                    for picking in self.loaded_picking_ids:
                        if not picking._check_backorder():
                            # no backorder needed means that all qty_done are
                            # set to fullfill the need => validate
                            picking.action_done()
                # Unplan moves that were not loaded and validated
                moves_to_unplan = self.loaded_move_line_ids.move_id.filtered(
                    lambda m: m.state not in ("cancel", "done") and not m.quantity_done
                )
                moves_to_unplan.shipment_advice_id = False
            shipment.departure_date = fields.Datetime.now()
            shipment.state = "done"
        return True

    def action_cancel(self):
        for shipment in self:
            if shipment.state not in ("confirmed", "in_progress"):
                raise UserError(
                    _("Shipment {} is not started, operation aborted.").format(
                        shipment.name
                    )
                )
            shipment.state = "cancel"

    def action_draft(self):
        for shipment in self:
            if shipment.state != "cancel":
                raise UserError(
                    _("Shipment {} is not canceled, operation aborted.").format(
                        shipment.name
                    )
                )
            shipment.state = "draft"

    def button_open_planned_pickings(self):
        action = self.env.ref("stock.action_picking_tree_all").read()[0]
        action["domain"] = [("id", "in", self.planned_picking_ids.ids)]
        return action

    def button_open_planned_moves(self):
        action = self.env.ref("stock.stock_move_action").read()[0]
        action["views"] = [
            (self.env.ref("stock.view_picking_move_tree").id, "tree"),
        ]
        action["domain"] = [("id", "in", self.planned_move_ids.ids)]
        action["context"] = {}  # Disable filters
        return action

    def button_open_loaded_pickings(self):
        action = self.env.ref("stock.action_picking_tree_all").read()[0]
        action["domain"] = [("id", "in", self.loaded_picking_ids.ids)]
        return action

    def button_open_loaded_move_lines(self):
        action = self.env.ref("stock.stock_move_line_action").read()[0]
        action["domain"] = [("id", "in", self.loaded_move_line_without_package_ids.ids)]
        action["context"] = {}  # Disable filters
        return action

    def button_open_loaded_packages(self):
        action = self.env.ref("stock.action_package_view").read()[0]
        action["domain"] = [("id", "in", self.loaded_package_ids.ids)]
        return action

    def button_open_deliveries_in_progress(self):
        action = self.env.ref("stock.action_picking_tree_all").read()[0]
        view_tree = self.env.ref(
            "shipment_advice.stock_picking_loading_progress_view_tree"
        )
        tree_view_index = action["views"].index((False, "tree"))
        action["views"][tree_view_index] = (view_tree.id, "tree")
        if self.planned_picking_ids:
            action["domain"] = [("id", "in", self.planned_picking_ids.ids)]
        else:
            domain = [
                ("picking_type_id.code", "=", self.shipment_type),
                ("state", "=", "assigned"),
                # Loaded in the current shipment or not loaded at all
                "|",
                ("move_line_ids.shipment_advice_id", "=", self.id),
                ("move_line_ids.shipment_advice_id", "=", False),
            ]
            if self.planned_move_ids:
                # and planned in the same shipment
                domain.append(("move_lines.shipment_advice_id", "=", self.id))
            else:
                domain.append(("move_lines.shipment_advice_id", "=", False))
            if self.carrier_ids:
                domain.append(("carrier_id", "in", self.carrier_ids.ids))
            pickings = self.env["stock.picking"].search(domain)
            action["domain"] = [("id", "in", pickings.ids)]
        return action

    def button_open_receptions_in_progress(self):
        action = self.env.ref("stock.action_picking_tree_all").read()[0]
        view_tree = self.env.ref(
            "shipment_advice.stock_picking_loading_progress_view_tree"
        )
        tree_view_index = action["views"].index((False, "tree"))
        action["views"][tree_view_index] = (view_tree.id, "tree")
        action["domain"] = [("id", "in", self.planned_picking_ids.ids)]
        return action
