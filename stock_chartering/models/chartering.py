from odoo import _, fields, models


class Chartering(models.Model):
    _name = "chartering"
    _description = "Freight informations"
    _inherit = ["mail.thread"]
    _order = "boarding_date, state DESC"
    _rec_names_search = ["carrier_id"]

    name = fields.Char()
    carrier_id = fields.Many2one(
        comodel_name="delivery.carrier",
        string="Boarding Charterer",
        tracking=True,
        help="Here is boarding charterer. Landing one can be different",
    )
    boarding_date = fields.Date(help="Expected/real boarding date", tracking=True)
    arrival_date = fields.Date(help="Expected/real arrival date", tracking=True)
    departure_id = fields.Many2one(
        comodel_name="res.partner",
        required=True,
        domain=[("is_boarding", "=", True)],
        tracking=True,
    )
    arrival_id = fields.Many2one(
        comodel_name="res.partner",
        domain=[("is_boarding", "=", True)],
        tracking=True,
    )
    vehicle_id = fields.Many2one(comodel_name="transport.vehicle", tracking=True)
    state = fields.Selection(
        selection=[
            ("pending", "Pending"),
            ("done", "Done"),
        ],
        default="pending",
        ondelete={"pending": "set default", "done": "set default"},
        tracking=True,
    )
    company_id = fields.Many2one(comodel_name="res.company", tracking=True)
    stock_move_ids = fields.Many2many(
        comodel_name="stock.move", compute="_compute_stock_moves"
    )

    def _compute_stock_moves(self):
        for rec in self:
            pickings = self.env["stock.picking"].search(
                [("chartering_id", "=", rec.id)]
            )
            rec.stock_move_ids = (
                self.env["stock.move"].search([("picking_id", "in", pickings.ids)]).ids
            )

    def ui_picking_action_done(self):
        "Validate picking"
        for rec in self:
            # TODO
            raise NotImplementedError

    def name_get(self):
        res = []
        for rec in self:
            string = rec._get_record_string()
            if self.env.context.get("short"):
                string = string[:10]
            res.append((rec.id, string))
        return res

    def _get_record_string(self):
        vehicles = {"ship": "🚢", "plane": "✈", "lorry": "🚚"}
        strings = []
        if self.name:
            strings.append(self.name)
        if self.departure_id:
            strings.append("%s ↪" % self.departure_id.name)
        if self.arrival_id:
            strings.append("%s" % self.arrival_id.name)
        if self.boarding_date:
            strings.append("📅 %s" % self.boarding_date)
        if self.vehicle_id:
            vehicle = vehicles.get(self.vehicle_id.type_, _("vehicle"))
            strings.append("%s %s" % (vehicle, self.vehicle_id.name))
        return ", ".join(strings)
