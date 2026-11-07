from odoo import api, fields, models
from odoo.exceptions import UserError

from odoo.addons.tms.models.tms_cargo import CONTAINER_TYPES, ULD_TYPES


class SaleOrderLineTripCargo(models.TransientModel):
    _name = "sale.order.line.trip.cargo"
    _description = "Sale Order Line Trip Cargo"

    wizard_id = fields.Many2one(
        "sale.order.line.trip", required=True, ondelete="cascade"
    )
    shipment_unit = fields.Selection(
        [
            ("cargo", "Cargo"),
            ("container", "Container"),
            ("uld", "ULD"),
        ],
        default="cargo",
    )
    name = fields.Char(string="Description")
    quantity = fields.Float(string="Quantity", default=1.0)
    uom_id = fields.Many2one(
        "uom.uom",
        string="Unit",
        default=lambda self: self.env.ref(
            "uom.product_uom_unit", raise_if_not_found=False
        ),
    )
    weight = fields.Float()
    weight_uom_id = fields.Many2one(
        "uom.uom",
        string="Weight unit",
        domain=lambda self: self.env["res.config.settings"]._weight_domain(),
        default=lambda self: self.env.ref(
            "uom.product_uom_kgm", raise_if_not_found=False
        ),
    )
    volume = fields.Float()
    volume_uom_id = fields.Many2one(
        "uom.uom",
        string="Volume unit",
        domain=lambda self: self.env["res.config.settings"]._volume_domain(),
        default=lambda self: self.env.ref(
            "uom.product_uom_cubic_meter", raise_if_not_found=False
        ),
    )
    container_type = fields.Selection(CONTAINER_TYPES, string="Container type")
    container_number = fields.Char(string="Container number")
    seal_number = fields.Char(string="Seal")
    uld_type = fields.Selection(ULD_TYPES, string="ULD type")
    uld_number = fields.Char(string="ULD number")


class SaleOrderLineTrip(models.TransientModel):
    _name = "sale.order.line.trip"
    _description = "Sale Order Line Trip"
    order_line_id = fields.Many2one("sale.order.line")
    product_template_id = fields.Many2one("product.template")
    shipment_unit = fields.Selection(
        [
            ("cargo", "Cargo"),
            ("container", "Container"),
            ("uld", "ULD"),
        ],
        compute="_compute_shipment_unit",
    )

    has_route = fields.Boolean(string="Use Routes")
    route = fields.Many2one("tms.route")
    origin = fields.Many2one(
        "res.partner",
        domain="[('tms_location', '=', True)]",
        context={"default_tms_location": True},
    )
    destination = fields.Many2one(
        "res.partner",
        domain="[('tms_location', '=', True)]",
        context={"default_tms_location": True},
    )
    start = fields.Datetime(string="Pickup date")
    end = fields.Datetime(string="Delivery date")
    cargo_line_ids = fields.One2many("sale.order.line.trip.cargo", "wizard_id")
    distance = fields.Float(string="Distance")
    distance_uom = fields.Char(string="Unit")
    distance_editable = fields.Boolean(compute="_compute_distance_editable")
    order_confirmed = fields.Boolean(readonly=True)
    partner_id = fields.Many2one("res.partner")
    allowed_rate_card_ids = fields.Many2many(
        "tms.rate.card",
        compute="_compute_allowed_rate_card_ids",
    )
    rate_card_id = fields.Many2one(
        "tms.rate.card",
        string="Rate card",
        domain="[('id', 'in', allowed_rate_card_ids)]",
    )

    @api.depends(
        "partner_id",
        "product_template_id",
        "product_template_id.transit_mode",
        "product_template_id.booking_type",
        "product_template_id.transport_type",
    )
    def _compute_allowed_rate_card_ids(self):
        cards = self.env["tms.rate.card"]
        for wizard in self:
            template = (
                wizard.product_template_id
                or wizard.order_line_id.product_id.product_tmpl_id
            )
            mode = template.transit_mode
            booking = template.booking_type
            if not mode or not booking:
                wizard.allowed_rate_card_ids = cards
                continue
            partner_ids = [False]
            if wizard.partner_id:
                partner_ids.extend(
                    (wizard.partner_id | wizard.partner_id.commercial_partner_id).ids
                )
            wizard.allowed_rate_card_ids = cards.search(
                [
                    ("transport_type", "=", template.transport_type),
                    ("transit_mode", "=", mode),
                    ("booking_type", "=", booking),
                    ("partner_id", "in", partner_ids),
                ]
            )

    @api.depends(
        "product_template_id",
        "product_template_id.transit_mode",
        "product_template_id.booking_type",
        "order_line_id",
        "order_line_id.product_id",
    )
    def _compute_shipment_unit(self):
        for wizard in self:
            template = (
                wizard.product_template_id
                or wizard.order_line_id.product_id.product_tmpl_id
            )
            if (
                template.transit_mode == "water"
                and template.booking_type == "full_asset"
            ):
                wizard.shipment_unit = "container"
            else:
                wizard.shipment_unit = "cargo"

    def _cargo_command_values(self, line, kilogram, cubic, unit):
        shipment_unit = line.get("shipment_unit") or self.shipment_unit or "cargo"
        values = {
            "shipment_unit": shipment_unit,
            "name": line.get("name")
            or self.env["tms.cargo"]._shipment_name_from_vals(
                {**line, "shipment_unit": shipment_unit}
            ),
            "quantity": line.get("quantity") or 1.0,
            "uom_id": line.get("uom_id") or (unit.id if unit else False),
            "weight": line.get("weight") or 0.0,
            "weight_uom_id": line.get("weight_uom_id")
            or (kilogram.id if kilogram else False),
            "volume": line.get("volume") or 0.0,
            "volume_uom_id": line.get("volume_uom_id")
            or (cubic.id if cubic else False),
            "container_type": line.get("container_type"),
            "container_number": line.get("container_number"),
            "seal_number": line.get("seal_number"),
            "uld_type": line.get("uld_type"),
            "uld_number": line.get("uld_number"),
        }
        return values

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        line_id = values.get("order_line_id") or self.env.context.get(
            "default_order_line_id"
        )
        line = self.env["sale.order.line"].browse(line_id)
        if "rate_card_id" in fields_list and not values.get("rate_card_id"):
            card = line.rate_card_id or line.order_id.rate_card_id
            if card:
                values["rate_card_id"] = card.id
        if "partner_id" in fields_list and not values.get("partner_id"):
            partner = line.order_id.partner_id
            if partner:
                values["partner_id"] = partner.id
        kilogram = self.env.ref("uom.product_uom_kgm", raise_if_not_found=False)
        cubic = self.env.ref("uom.product_uom_cubic_meter", raise_if_not_found=False)
        unit = self.env.ref("uom.product_uom_unit", raise_if_not_found=False)
        lines = self.env.context.get("cargo_lines_default") or []
        if not lines and self.env.context.get("default_order_line_id"):
            domain = [
                ("sale_line_id", "=", self.env.context["default_order_line_id"]),
            ]
            if "parent_id" in self.env["tms.cargo"]._fields:
                domain.append(("parent_id", "=", False))
            cargo = self.env["tms.cargo"].search(domain)
            lines = [
                {
                    "shipment_unit": item.shipment_unit,
                    "name": item.name,
                    "quantity": item.quantity,
                    "uom_id": item.uom_id.id,
                    "weight": item.weight,
                    "weight_uom_id": item.weight_uom_id.id,
                    "volume": item.volume,
                    "volume_uom_id": item.volume_uom_id.id,
                    "container_type": item.container_type,
                    "container_number": item.container_number,
                    "seal_number": item.seal_number,
                    "uld_type": item.uld_type,
                    "uld_number": item.uld_number,
                }
                for item in cargo
            ]
        if "cargo_line_ids" in fields_list and lines:
            commands = []
            for line in lines:
                if (
                    not line.get("name")
                    and not line.get("container_type")
                    and not line.get("uld_type")
                ):
                    continue
                commands.append(
                    (0, 0, self._cargo_command_values(line, kilogram, cubic, unit))
                )
            values["cargo_line_ids"] = commands
        return values

    def _apply_route_distance(self):
        self.ensure_one()
        if self.has_route and self.route and self.route.distance:
            self.distance = self.route.distance
            self.distance_uom = self.route.distance_uom.name
            return True
        return False

    def _apply_provider_distance(self):
        self.ensure_one()
        route_model = self.env["tms.route"]
        if not hasattr(route_model, "_distance_between_partners"):
            return False
        if not self.origin or not self.destination:
            return False
        distance, uom = route_model._distance_between_partners(
            self.origin, self.destination
        )
        self.distance = distance
        self.distance_uom = uom.name if uom else False
        return True

    @api.depends_context("uid")
    def _compute_distance_editable(self):
        editable = not self.env["tms.route"]._routing_provider_ready()
        for wizard in self:
            wizard.distance_editable = editable

    @api.onchange("origin", "destination", "has_route", "route")
    def _onchange_distance(self):
        if self._apply_route_distance():
            return
        if not self.env["tms.route"]._routing_provider_ready():
            return
        if not self.origin or not self.destination:
            return
        try:
            self._apply_provider_distance()
        except UserError as error:
            return {
                "warning": {
                    "title": self.env._("Distance"),
                    "message": str(error),
                }
            }

    @api.onchange("origin", "destination", "start", "end", "has_route", "route")
    def _compute_readonly_fields(self):
        state = self.order_line_id.order_id.state
        if state == "sale" or state == "cancel":
            self.order_confirmed = True
        else:
            self.order_confirmed = False
