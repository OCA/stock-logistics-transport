from odoo import api, fields, models


class TMSOrderOptimizer(models.Model):
    """Extension of tms.order with optimization-related fields."""

    _inherit = "tms.order"

    is_locked_for_optimization = fields.Boolean(
        default=False,
        string="Locked for Optimization",
        help="When checked, this order cannot be included in route recalculations",
    )
    can_recalculate = fields.Boolean(
        compute="_compute_can_recalculate",
        help="Indicates if this order can be included in a route recalculation",
    )
    # Note: optimizer_id cannot point to TransientModel, so we store a reference
    # to the optimization name/date instead
    optimization_source = fields.Char(
        readonly=True,
        help="Reference to the optimization that created this order",
    )

    @api.depends("stage_id", "stage_id.is_completed", "is_locked_for_optimization")
    def _compute_can_recalculate(self):
        """
        Determine if an order can be recalculated.

        An order can be recalculated if:
        - It's not locked for optimization
        - Its stage is not completed
        - None of its stops have been delivered
        """
        for order in self:
            # Basic checks
            if order.is_locked_for_optimization:
                order.can_recalculate = False
                continue

            if order.stage_id and order.stage_id.is_completed:
                order.can_recalculate = False
                continue

            # Check if any stops have been delivered
            # This depends on tms_delivery_stops module
            stop_ids = order.stop_ids if hasattr(order, "stop_ids") else []
            has_delivered = any(
                getattr(s, "state", None) == "delivered" for s in stop_ids
            )

            order.can_recalculate = not has_delivered
