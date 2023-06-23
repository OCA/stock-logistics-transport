from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    chartering_id = fields.Many2one(
        comodel_name="chartering", domain=[("state", "=", "pending")]
    )
    container = fields.Char()
    container_lot = fields.Char(help="Complementary info about chartering container")

    @api.depends("chartering_id")
    def _compute_charterer_carrier(self):
        for rec in self:
            if not rec.carrier_id and rec.chartering_id.carrier_id:
                rec.carrier_id = rec.chartering_id.carrier_id.id

    def _action_done(self):
        res = super()._action_done()
        for rec in self:
            if rec.chartering_id and rec.chartering_id.state != "done":
                states = self.search([("carrier_id", "=", rec.carrier_id.id)]).mapped(
                    "state"
                )
                if states and len(states) == 1 and states[0] == "done":
                    rec.chartering_id.state = "done"
        return res
