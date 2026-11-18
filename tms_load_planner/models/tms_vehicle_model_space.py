# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class TmsVehicleModelSpace(models.Model):
    """Static seat, cabin, or row on a vehicle model.

    The layout belongs to the model. Each vehicle of that model gets its
    own tms.vehicle.space rows from these slots.
    """

    _name = "tms.vehicle.model.space"
    _description = "Vehicle model space"
    _order = "pos_x, pos_y, pos_z, code, id"
    _rec_name = "code"

    model_id = fields.Many2one(
        "fleet.vehicle.model",
        string="Vehicle model",
        required=True,
        ondelete="cascade",
        index=True,
    )
    code = fields.Char(required=True, help="For example SEAT-01, CABIN-A, ROW-1-LEFT.")
    zone = fields.Selection(
        [
            ("front", "Front"),
            ("center", "Center"),
            ("rear", "Rear"),
        ],
        required=True,
        default="center",
    )
    is_premium = fields.Boolean(string="Premium")
    pos_x = fields.Float(
        string="X (m)",
        help="Meters from the front of the loading box, along its length.",
    )
    pos_y = fields.Float(
        string="Y (m)",
        help="Meters from the left side of the loading box.",
    )
    pos_z = fields.Float(
        string="Z (m)",
        help="Meters up from the floor.",
    )
    size_length = fields.Float(string="Length (m)")
    size_width = fields.Float(string="Width (m)")
    size_height = fields.Float(string="Height (m)")
    vehicle_space_ids = fields.One2many(
        "tms.vehicle.space",
        "model_space_id",
        string="Vehicle spaces",
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        vehicles = self.env["fleet.vehicle"].search(
            [("model_id", "in", records.model_id.ids)]
        )
        vehicles._sync_model_spaces()
        trips = self.env["tms.order"].search([("vehicle_id", "in", vehicles.ids)])
        for trip in trips:
            trip._sync_space_allocations()
        return records

    def overlaps_xy(self, other):
        """True when the two slots share floor area."""
        self.ensure_one()
        other.ensure_one()
        tolerance = 0.05
        return (
            self.pos_x < other.pos_x + other.size_length - tolerance
            and other.pos_x < self.pos_x + self.size_length - tolerance
            and self.pos_y < other.pos_y + other.size_width - tolerance
            and other.pos_y < self.pos_y + self.size_width - tolerance
        )

    def supporting_space(self, spaces):
        """The slot directly underneath, when its top reaches this floor."""
        self.ensure_one()
        best = self.browse()
        best_top = None
        for other in spaces:
            if other.id == self.id or not self.overlaps_xy(other):
                continue
            top = other.pos_z + (other.size_height or 0.0)
            if top > self.pos_z + 0.05 or self.pos_z - top > 0.2:
                continue
            if best_top is None or top > best_top:
                best = other
                best_top = top
        return best
