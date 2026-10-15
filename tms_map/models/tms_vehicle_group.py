from odoo import fields, models


class TmsVehicleGroup(models.Model):
    _name = "tms.vehicle.group"
    _description = "Vehicle Group"
    _order = "name"

    name = fields.Char(required=True)
    vehicle_ids = fields.Many2many(
        comodel_name="fleet.vehicle",
        relation="tms_vehicle_group_vehicle_rel",
        column1="group_id",
        column2="vehicle_id",
        string="Vehicles",
    )
