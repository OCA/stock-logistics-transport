from odoo import api, fields, models


class TMSRouteOptimizerResult(models.TransientModel):
    _name = "tms.route.optimizer.result"
    _description = "TMS Route Optimizer Result"

    optimizer_id = fields.Many2one(
        "tms.route.optimizer",
        string="Optimizer",
        required=True,
        ondelete="cascade",
    )
    day_result_id = fields.Many2one(
        "tms.route.optimizer.day.result",
        string="Day Result",
        ondelete="cascade",
    )
    planning_date = fields.Date(
        related="day_result_id.planning_date",
        store=True,
        string="Planning Date",
    )
    vehicle_id = fields.Many2one(
        "fleet.vehicle",
        string="Vehicle",
        # Not required for vehicle_types mode where we may not have a real vehicle
    )
    vehicle_type_id = fields.Many2one(
        "fleet.vehicle.type",
        string="Vehicle Type",
        # Stored directly, not related, to support vehicle_types mode
    )
    order_id = fields.Many2one(
        "tms.order",
        string="Created Order",
    )
    stop_ids = fields.Many2many(
        "tms.order.stop",
        string="Delivery Stops",
    )
    stop_count = fields.Integer()
    total_distance = fields.Float(
        string="Total Distance (km)",
    )
    total_time = fields.Float(
        string="Total Time (hours)",
    )
    total_weight = fields.Float(
        string="Total Weight (kg)",
    )
    total_volume = fields.Float(
        string="Total Volume (m³)",
    )
    total_packages = fields.Integer(
        compute="_compute_total_packages",
    )
    weight_utilization = fields.Float(
        string="Weight Utilization (%)",
    )
    volume_utilization = fields.Float(
        string="Volume Utilization (%)",
    )
    route_cost = fields.Float()
    cost_per_km = fields.Float(
        string="Cost per KM",
    )
    google_maps_url = fields.Char(
        string="Google Maps URL",
    )
    route_sequence = fields.Text(
        string="Route Sequence (JSON)",
    )

    @api.depends("stop_ids.package_count")
    def _compute_total_packages(self):
        for result in self:
            result.total_packages = sum(result.stop_ids.mapped("package_count"))
