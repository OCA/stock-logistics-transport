from odoo import api, fields, models


class TMSRouteOptimizerDayResult(models.TransientModel):
    _name = "tms.route.optimizer.day.result"
    _description = "TMS Route Optimizer Daily Result"
    _order = "planning_date"

    optimizer_id = fields.Many2one(
        "tms.route.optimizer",
        required=True,
        ondelete="cascade",
    )
    planning_date = fields.Date(required=True)
    result_ids = fields.One2many(
        "tms.route.optimizer.result",
        "day_result_id",
        string="Routes",
    )
    total_stops = fields.Integer(
        compute="_compute_totals",
        store=True,
    )
    total_distance = fields.Float(
        compute="_compute_totals",
        store=True,
        string="Total Distance (km)",
    )
    total_cost = fields.Float(
        compute="_compute_totals",
        store=True,
    )
    total_packages = fields.Integer(
        compute="_compute_totals",
        store=True,
    )
    total_vehicles = fields.Integer(
        compute="_compute_totals",
        store=True,
        string="Vehicles Used",
    )
    unassigned_stop_ids = fields.Many2many(
        "tms.order.stop",
        "tms_route_optimizer_day_unassigned_rel",
        "day_result_id",
        "stop_id",
        string="Unassigned Stops",
        help="Stops that could not be assigned on this day",
    )
    unassigned_count = fields.Integer(
        compute="_compute_unassigned_count",
        string="Unassigned",
    )

    @api.depends(
        "result_ids",
        "result_ids.stop_count",
        "result_ids.total_distance",
        "result_ids.route_cost",
        "result_ids.total_packages",
    )
    def _compute_totals(self):
        for day in self:
            day.total_stops = sum(day.result_ids.mapped("stop_count"))
            day.total_distance = sum(day.result_ids.mapped("total_distance"))
            day.total_cost = sum(day.result_ids.mapped("route_cost"))
            day.total_vehicles = len(day.result_ids)
            day.total_packages = sum(day.result_ids.mapped("total_packages"))

    @api.depends("unassigned_stop_ids")
    def _compute_unassigned_count(self):
        for day in self:
            day.unassigned_count = len(day.unassigned_stop_ids)
