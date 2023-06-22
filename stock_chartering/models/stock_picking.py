from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    chartering_id = fields.Many2one(comodel_name="chartering")
    container_id = fields.Many2one(
        comodel_name="freight.container",
        compute="_compute_freight_container",
        readonly=False,
        store=True,
    )
    container_note = fields.Char(help="Complementary info about chartering container")

    @api.depends("chartering_id")
    def _compute_freight_container(self):
        for rec in self:
            if not rec.container_id and rec.chartering_id.first_container_id:
                rec.container_id = rec.chartering_id.first_container_id.id

    def _action_done(self):
        res = super()._action_done()
        for rec in self:
            if rec.chartering_id and rec.chartering_id.state != "done":
                states = self.search(
                    [("charterer_id", "=", rec.charterer_id.id)]
                ).mapped("state")
                if states and len(states) == 1 and states[0] == "done":
                    rec.chartering_id.state = "done"
        return res
