from odoo import fields, models


class TransportVehicle(models.Model):
    _name = "transport.vehicle"
    _description = "Ship, plane or Lorry"
    _inherit = ["mail.thread"]

    name = fields.Char(required=True)
    type_ = fields.Selection(
        selection=[
            ("ship", "Ship"),
            ("plane", "Plane"),
            ("lorry", "Lorry"),
        ],
        default="ship",
        ondelete={
            "ship": "set default",
            "plane": "set default",
            "lorry": "set default",
        },
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(comodel_name="res.company")
