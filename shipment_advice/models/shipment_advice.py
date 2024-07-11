# Copyright 2021 Camptocamp SA
# Copyright 2024 Michael Tietz (MT Software) <mtietz@mt-software.de>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ShipmentAdvice(models.Model):
    _name = "shipment.advice"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Shipment Advice"
    _order = "arrival_date DESC, id DESC"

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
        string="Total load (kg)",
        digits=(16, 2),
        compute="_compute_total_load",
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
    to_validate_picking_ids = fields.One2many(
        comodel_name="stock.picking",
        compute="_compute_picking_ids",
        string="Transfers to validate",
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
    line_to_load_ids = fields.One2many(
        comodel_name="stock.move.line",
        compute="_compute_line_to_load_ids",
        help=(
            "Lines to load in priority.\n"
            "If the shipment is planned, it'll return the planned lines.\n"
            "If the shipment is not planned, it'll return lines from transfers "
            "partially loaded."
        ),
    )
    lines_to_load_count = fields.Integer(compute="_compute_count")
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

    def _find_move_lines_domain(self, picking_type_ids=None):
        """Returns the base domain to look for move lines for a given shipment."""
        self.ensure_one()
        domain = [
            ("state", "in", ("assigned", "partially_available")),
            ("picking_code", "=", self.shipment_type),
            "|",
            ("shipment_advice_id", "=", False),
            ("shipment_advice_id", "=", self.id),
        ]
        # Restrict on picking types if provided
        if picking_type_ids:
            domain.insert(0, ("picking_id.picking_type_id", "in", picking_type_ids.ids))
        else:
            domain.insert(
                0,
                ("picking_id.picking_type_id.warehouse_id", "=", self.warehouse_id.id),
            )
        # Shipment with planned content, restrict the search to it
        if self.planned_move_ids:
            domain.append(("move_id.shipment_advice_id", "=", self.id))
        # Shipment without planned content, search for all unplanned moves
        else:
            domain.append(("move_id.shipment_advice_id", "=", False))
            # Restrict to shipment carrier delivery types (providers)
            if self.carrier_ids:
                domain.extend(
                    [
                        "|",
                        (
                            "picking_id.carrier_id.delivery_type",
                            "in",
                            self.carrier_ids.mapped("delivery_type"),
                        ),
                        ("picking_id.carrier_id", "=", False),
                    ]
                )
        return domain

    @api.depends("planned_move_ids")
    @api.depends_context("shipment_picking_type_ids")
    def _compute_line_to_load_ids(self):
        picking_type_ids = self.env.context.get("shipment_picking_type_ids", [])
        for shipment in self:
            domain = shipment._find_move_lines_domain(picking_type_ids)
            # Restrict to lines not loaded
            domain.insert(0, ("shipment_advice_id", "=", False))
            # Find lines to load from partially loaded transfers if the shipment
            # is not planned.
            if not shipment.planned_move_ids:
                all_lines_to_load = self.env["stock.move.line"].search(domain)
                all_pickings = all_lines_to_load.picking_id
                loaded_lines = self.env["stock.move.line"].search(
                    [
                        ("picking_id", "in", all_pickings.ids),
                        ("id", "not in", all_lines_to_load.ids),
                        ("shipment_advice_id", "!=", False),
                    ]
                )
                pickings_partially_loaded = loaded_lines.picking_id
                domain += [("picking_id", "in", pickings_partially_loaded.ids)]
            shipment.line_to_load_ids = self.env["stock.move.line"].search(domain)

    def _check_include_package_level(self, package_level):
        """Check if a package level should be listed in the shipment advice.

        Aim to be overridden by sub-modules.
        """
        return True

    @api.depends("loaded_move_line_ids.result_package_id.shipping_weight")
    def _compute_total_load(self):
        for shipment in self:
            packages = shipment.loaded_move_line_ids.result_package_id
            shipment.total_load = sum(packages.mapped("shipping_weight"))

    @api.depends(
        "planned_move_ids", "loaded_move_line_ids.picking_id.loaded_shipment_advice_ids"
    )
    def _compute_picking_ids(self):
        for shipment in self:
            shipment.planned_picking_ids = shipment.planned_move_ids.picking_id
            shipment.loaded_picking_ids = shipment.loaded_move_line_ids.picking_id
            # Transfers to validate are those having only the current shipment
            # advice to process
            to_validate_picking_ids = []
            for picking in shipment.loaded_move_line_ids.picking_id:
                shipments_to_process = picking.loaded_shipment_advice_ids.filtered(
                    lambda s: s.state not in ("done", "cancel")
                )
                if shipments_to_process == shipment:
                    to_validate_picking_ids.append(picking.id)
            shipment.to_validate_picking_ids = self.env["stock.picking"].browse(
                to_validate_picking_ids
            )

    @api.depends(
        "loaded_move_line_ids.package_level_id.package_id",
    )
    def _compute_package_ids(self):
        for shipment in self:
            package_levels = shipment.loaded_move_line_ids.package_level_id
            shipment.loaded_package_level_ids = package_levels.filtered(
                self._check_include_package_level
            )
            package_ids = set()
            for line in shipment.loaded_move_line_ids:
                if line.package_level_id and self._check_include_package_level(
                    line.package_level_id
                ):
                    package_ids.add(line.package_level_id.package_id.id)
            shipment.loaded_package_ids = self.env["stock.quant.package"].browse(
                package_ids
            )

    @api.depends("planned_picking_ids", "planned_move_ids", "line_to_load_ids")
    def _compute_count(self):
        for shipment in self:
            shipment.planned_pickings_count = len(shipment.planned_picking_ids)
            shipment.planned_moves_count = len(shipment.planned_move_ids)
            shipment.loaded_pickings_count = len(shipment.loaded_picking_ids)
            shipment.loaded_move_lines_without_package_count = len(
                shipment.loaded_move_line_without_package_ids
            )
            shipment.loaded_packages_count = len(shipment.loaded_package_ids)
            shipment.lines_to_load_count = len(shipment.line_to_load_ids)

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
        if vals.get("shipment_type", defaults["shipment_type"]) == "incoming":
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

    def _lock_records(self, records):
        """Lock records for the current SQL transaction."""
        sql = "SELECT id FROM %s WHERE ID IN %%s FOR UPDATE" % records._table
        self.env.cr.execute(sql, (tuple(records.ids),), log_exceptions=False)

    def _close_pickings(self):
        """Validate transfers (create backorders for unprocessed lines)"""
        self.ensure_one()
        wiz_model = self.env["stock.backorder.confirmation"]
        pickings = self.env["stock.picking"]
        create_backorder = True
        if self.shipment_type == "incoming":
            self._lock_records(self.planned_picking_ids)
            pickings = self.planned_picking_ids
        else:
            self._lock_records(self.loaded_picking_ids)
            pickings = self.to_validate_picking_ids
            create_backorder = (
                self.company_id.shipment_advice_outgoing_backorder_policy
                == "create_backorder"
            )
        for picking in pickings:
            if picking.state in ("cancel", "done"):
                continue
            if picking._check_backorder():
                if not create_backorder:
                    continue
                wiz = wiz_model.create({})
                wiz.pick_ids = picking
                wiz.with_context(button_validate_picking_ids=picking.ids).process()
            else:
                picking._action_done()

    def _unplan_loaded_moves(self):
        """Unplan moves that were not loaded and validated"""
        moves_to_unplan = self.loaded_move_line_ids.move_id.filtered(
            lambda m: m.state not in ("cancel", "done") and not m.quantity_done
        )
        moves_to_unplan.shipment_advice_id = False

    def action_done(self):
        shipment_advice_ids_to_validate = []
        self = self.with_context(shipment_advice_ignore_auto_close=True)
        for shipment in self:
            if shipment.state != "in_progress":
                raise UserError(
                    _("Shipment {} is not started, operation aborted.").format(
                        shipment.name
                    )
                )
            shipment._close_pickings()
            if shipment.shipment_type == "outgoing":
                shipment._unplan_loaded_moves()
            shipment_advice_ids_to_validate.append(shipment.id)
        if shipment_advice_ids_to_validate:
            self.browse(shipment_advice_ids_to_validate)._action_done()
        return True

    def _action_done(self):
        self.write({"departure_date": fields.Datetime.now(), "state": "done"})

    def auto_close_incoming_shipment_advices(self):
        """Set incoming shipment advice to done when all planned moves are processed"""
        if self.env.context.get("shipment_advice_ignore_auto_close"):
            return
        shipment_ids_to_close = []
        for shipment in self:
            if (
                shipment.shipment_type != "incoming"
                or not shipment.company_id.shipment_advice_auto_close_incoming
                or any(
                    move.state not in ("cancel", "done")
                    for move in shipment.planned_move_ids
                )
            ):
                continue
            shipment_ids_to_close.append(shipment.id)
        if shipment_ids_to_close:
            self.browse(shipment_ids_to_close)._action_done()

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
        action_xmlid = "stock.action_picking_tree_all"
        action = self.env["ir.actions.act_window"]._for_xml_id(action_xmlid)
        action["domain"] = [("id", "in", self.planned_picking_ids.ids)]
        return action

    def button_open_planned_moves(self):
        action_xmlid = "stock.stock_move_action"
        action = self.env["ir.actions.act_window"]._for_xml_id(action_xmlid)
        action["views"] = [
            (self.env.ref("stock.view_picking_move_tree").id, "tree"),
        ]
        action["domain"] = [("id", "in", self.planned_move_ids.ids)]
        action["context"] = {}  # Disable filters
        return action

    def button_open_loaded_pickings(self):
        action_xmlid = "stock.action_picking_tree_all"
        action = self.env["ir.actions.act_window"]._for_xml_id(action_xmlid)
        action["domain"] = [("id", "in", self.loaded_picking_ids.ids)]
        return action

    def button_open_loaded_move_lines(self):
        action_xmlid = "stock.stock_move_line_action"
        action = self.env["ir.actions.act_window"]._for_xml_id(action_xmlid)
        action["domain"] = [("id", "in", self.loaded_move_line_without_package_ids.ids)]
        action["context"] = {}  # Disable filters
        return action

    def button_open_loaded_packages(self):
        action_xmlid = "stock.action_package_view"
        action = self.env["ir.actions.act_window"]._for_xml_id(action_xmlid)
        action["domain"] = [("id", "in", self.loaded_package_ids.ids)]
        return action

    def button_open_to_load_move_lines(self):
        action_xmlid = "stock.stock_move_line_action"
        action = self.env["ir.actions.act_window"]._for_xml_id(action_xmlid)
        action["domain"] = [("id", "in", self.line_to_load_ids.ids)]
        action["context"] = {}  # Disable filters
        return action

    def _domain_open_deliveries_in_progress(self):
        self.ensure_one()
        domain = []
        if self.planned_picking_ids:
            domain += [
                ("picking_type_id.warehouse_id", "=", self.warehouse_id.id),
                ("id", "in", self.planned_picking_ids.ids),
            ]
        else:
            domain += [
                ("picking_type_id.code", "=", self.shipment_type),
                ("picking_type_id.warehouse_id", "=", self.warehouse_id.id),
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
        return domain

    def button_open_deliveries_in_progress(self):
        action_xmlid = "stock.action_picking_tree_all"
        action = self.env["ir.actions.act_window"]._for_xml_id(action_xmlid)
        view_tree = self.env.ref(
            "shipment_advice.stock_picking_loading_progress_view_tree"
        )
        tree_view_index = action["views"].index((False, "tree"))
        action["views"][tree_view_index] = (view_tree.id, "tree")
        action["domain"] = self._domain_open_deliveries_in_progress()
        return action

    def button_open_receptions_in_progress(self):
        action_xmlid = "stock.action_picking_tree_all"
        action = self.env["ir.actions.act_window"]._for_xml_id(action_xmlid)
        view_tree = self.env.ref(
            "shipment_advice.stock_picking_loading_progress_view_tree"
        )
        tree_view_index = action["views"].index((False, "tree"))
        action["views"][tree_view_index] = (view_tree.id, "tree")
        action["domain"] = [("id", "in", self.planned_picking_ids.ids)]
        return action
