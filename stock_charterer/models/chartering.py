from odoo import _, fields, models


class Chartering(models.Model):
    _name = "chartering"
    _description = "Freight informations"
    _inherit = ["mail.thread"]
    _order = "boarding_date, state DESC"
    _rec_names_search = ["charterer_id"]

    charterer_id = fields.Many2one(
        comodel_name="res.partner",
        required=True,
        domain=[("is_charterer", "=", True)],
        tracking=True,
    )
    boarding_date = fields.Date(help="Expected boarding date", tracking=True)
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
    first_container_id = fields.Many2one(
        comodel_name="freight.container", tracking=True
    )
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

    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id, rec._get_record_string()))
        return res

    def _get_record_string(self):
        vehicles = {"ship": "🚢", "plane": "✈", "lorry": "🚚"}
        strings = []
        if self.departure_id:
            strings.append("%s %s" % (_("from"), self.departure_id.name))
        if self.arrival_id:
            strings.append("%s %s" % (_("to"), self.arrival_id.name))
        if self.boarding_date:
            strings.append("📅 %s" % self.boarding_date)
        if self.charterer_id:
            strings.append("🏢 %s" % self.charterer_id.name)
        if self.vehicle_id:
            vehicle = vehicles.get(self.vehicle_id.type_, _("vehicle"))
            strings.append("%s %s" % (vehicle, self.vehicle_id.name))
        return ", ".join(strings)
