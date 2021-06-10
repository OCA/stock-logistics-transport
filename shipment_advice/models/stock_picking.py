# Copyright 2021 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import api, fields, models
from odoo.tools import float_round


class StockPicking(models.Model):
    _inherit = "stock.picking"

    planned_shipment_advice_id = fields.Many2one(
        comodel_name="shipment.advice",
        related="move_lines.shipment_advice_id",
        store=True,
        index=True,
    )
    is_fully_loaded_in_shipment = fields.Boolean(
        string="Is fully loaded in a shipment?", compute="_compute_loaded_in_shipment",
    )
    is_partially_loaded_in_shipment = fields.Boolean(
        string="Is partially loaded in a shipment?",
        compute="_compute_loaded_in_shipment",
    )
    loaded_packages_count = fields.Integer(
        "Packages loaded", compute="_compute_shipment_loaded_progress",
    )
    total_packages_count = fields.Integer(
        "Total packages", compute="_compute_shipment_loaded_progress",
    )
    loaded_move_lines_count = fields.Integer(
        "Bulk lines loaded", compute="_compute_shipment_loaded_progress",
    )
    total_move_lines_count = fields.Integer(
        "Total bulk lines", compute="_compute_shipment_loaded_progress",
    )
    loaded_packages_progress_f = fields.Float(
        "Packages loaded/total %",
        digits=(3, 2),
        compute="_compute_shipment_loaded_progress",
    )
    loaded_move_lines_progress_f = fields.Float(
        "Bulk lines loaded/total %",
        digits=(3, 2),
        compute="_compute_shipment_loaded_progress",
    )
    loaded_progress_f = fields.Float(
        "Loaded/total %", digits=(3, 2), compute="_compute_shipment_loaded_progress"
    )
    loaded_progress = fields.Char(
        "Loaded/total", compute="_compute_shipment_loaded_progress"
    )
    loaded_packages_progress = fields.Char(
        "Packages loaded/total", compute="_compute_shipment_loaded_progress"
    )
    loaded_move_lines_progress = fields.Char(
        "Bulk lines loaded/total", compute="_compute_shipment_loaded_progress"
    )
    loaded_weight = fields.Integer(
        "Loaded weight", compute="_compute_shipment_loaded_progress"
    )
    loaded_weight_progress = fields.Char(
        "Weight/total", compute="_compute_shipment_loaded_progress"
    )
    loaded_shipment_advice_ids = fields.Many2many(
        "shipment.advice", compute="_compute_loaded_in_shipment",
    )

    @api.depends("move_line_ids.shipment_advice_id")
    def _compute_loaded_in_shipment(self):
        for picking in self:
            picking.is_fully_loaded_in_shipment = all(
                line.shipment_advice_id and line.qty_done == line.product_uom_qty
                for line in picking.move_line_ids
            )
            picking.is_partially_loaded_in_shipment = (
                not picking.is_fully_loaded_in_shipment
                and any(
                    line.shipment_advice_id and line.qty_done > 0
                    for line in picking.move_line_ids
                )
            )
            picking.loaded_shipment_advice_ids = (
                picking.move_line_ids.shipment_advice_id
            )

    @api.depends("package_level_ids.package_id", "move_line_ids")
    def _compute_shipment_loaded_progress(self):
        for picking in self:
            picking.loaded_packages_count = 0
            picking.loaded_move_lines_count = 0
            picking.loaded_packages_progress_f = 0.0
            picking.loaded_move_lines_progress_f = 0.0
            picking.loaded_progress_f = 0.0
            picking.loaded_packages_progress = ""
            picking.loaded_move_lines_progress = ""
            picking.loaded_weight = 0
            picking.loaded_weight_progress = ""
            picking.total_packages_count = len(picking.package_level_ids.package_id)
            picking.total_move_lines_count = len(picking.move_line_ids_without_package)
            # Packages loading progress
            if picking.total_packages_count:
                picking.loaded_packages_count = len(
                    [
                        pl
                        for pl in picking.package_level_ids
                        if pl.shipment_advice_id and pl.is_done
                    ]
                )
                picking.loaded_packages_progress_f = (
                    picking.loaded_packages_count / picking.total_packages_count
                )
                picking.loaded_packages_progress = (
                    f"{picking.loaded_packages_count} / {picking.total_packages_count}"
                )
            # Lines loading progress
            if picking.total_move_lines_count:
                picking.loaded_move_lines_count = len(
                    [
                        ml
                        for ml in picking.move_line_ids_without_package
                        if ml.shipment_advice_id and ml.qty_done > 0
                    ]
                )
                picking.loaded_move_lines_progress_f = (
                    picking.loaded_move_lines_count / picking.total_move_lines_count
                )
                picking.loaded_move_lines_progress = (
                    f"{picking.loaded_move_lines_count} "
                    f"/ {picking.total_move_lines_count}"
                )
            # Weight/total
            if picking.shipping_weight:
                # FIXME: not sure how to get the weight of bulk line?
                picking.loaded_weight = sum(
                    [
                        ml.result_package_id.shipping_weight or ml.move_id.weight
                        for ml in picking.move_line_ids_without_package
                        if ml.shipment_advice_id and ml.qty_done > 0
                    ]
                ) + sum(
                    [
                        pl.package_id.shipping_weight
                        for pl in picking.package_level_ids
                        if pl.shipment_advice_id and pl.is_done
                    ]
                )
                total_weight = float_round(
                    picking.shipping_weight, precision_rounding=0.01,
                )
                picking.loaded_weight_progress = (
                    f"{picking.loaded_weight} / {total_weight}"
                )
            # Overall progress based on the operation type
            if picking.picking_type_id.show_entire_packs:
                picking.loaded_progress_f = picking.loaded_packages_progress_f
                picking.loaded_progress = picking.loaded_packages_progress
            else:
                picking.loaded_progress_f = picking.loaded_move_lines_progress_f
                picking.loaded_progress = picking.loaded_move_lines_progress

    def button_plan_in_shipment(self):
        action = self.env.ref(
            "shipment_advice.wizard_plan_shipment_picking_action"
        ).read()[0]
        action["context"] = {"active_model": self._name, "active_ids": self.ids}
        return action

    def button_load_in_shipment(self):
        action = self.env.ref(
            "shipment_advice.wizard_load_shipment_picking_action"
        ).read()[0]
        action["context"] = {"active_model": self._name, "active_ids": self.ids}
        return action

    def button_unload_from_shipment(self):
        action = self.env.ref(
            "shipment_advice.wizard_unload_shipment_picking_action"
        ).read()[0]
        action["context"] = {"active_model": self._name, "active_ids": self.ids}
        return action

    def _plan_in_shipment(self, shipment_advice):
        """Plan the whole transfers content into the given shipment advice."""
        self.move_lines._plan_in_shipment(shipment_advice)

    def _load_in_shipment(self, shipment_advice):
        """Load the whole transfers content into the given shipment advice."""
        self.package_level_ids._load_in_shipment(shipment_advice)
        self.move_line_ids._load_in_shipment(shipment_advice)

    def _unload_from_shipment(self):
        """Unload the whole transfers content from their related shipment advice."""
        self.package_level_ids._unload_from_shipment()
        self.move_line_ids._unload_from_shipment()
