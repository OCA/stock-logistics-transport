# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

_DEMO_KINDS = {
    "model_category_tractor": "pallet",
    "model_category_box_truck": "box",
    "model_category_coach": "coach",
    "model_category_city_bus": "city",
    "model_category_container_ship": "ship",
    "model_category_cruise_ship": "cabin",
    "model_category_ferry": "cabin",
    "model_category_freighter": "freighter",
    "model_category_narrow_body": "narrow",
    "model_category_wide_body": "wide",
    "model_category_regional": "narrow",
    "model_category_business_jet": "jet",
}


class FleetVehicleModel(models.Model):
    _inherit = "fleet.vehicle.model"

    max_pallet_positions = fields.Integer(
        related="pallet_capacity",
        string="Max pallet positions",
        readonly=False,
    )
    space_ids = fields.One2many(
        "tms.vehicle.model.space", "model_id", string="Spaces"
    )
    layout_image = fields.Binary(
        string="Layout plan",
        attachment=True,
        help="Top view of the loading box. The left edge of the picture is the front.",
    )

    def _demo_xmlid_name(self):
        self.ensure_one()
        xmlid = self.get_external_id().get(self.id, "")
        return xmlid.split(".")[-1]

    def _demo_space_kind(self):
        """Layout family for a catalog model that has no spaces yet."""
        self.ensure_one()
        name = self._demo_xmlid_name()
        if name == "demo_model_dolly":
            return ""
        if name == "demo_model_dry_van":
            return "dry_van"
        category = self.category_id
        if not category:
            return ""
        category_name = category.get_external_id().get(category.id, "")
        return _DEMO_KINDS.get(category_name.split(".")[-1], "")

    def _demo_space_slots(self):
        """Slot dicts for this model. Empty when the model is not a demo layout."""
        self.ensure_one()
        builders = {
            "pallet": lambda: self._demo_pallet_slots(8, top_rows=1),
            "box": lambda: self._demo_pallet_slots(5),
            "dry_van": lambda: self._demo_pallet_slots(12),
            "freighter": lambda: self._demo_pallet_slots(6),
            "coach": lambda: self._demo_seat_slots(10, "SEAT"),
            "city": lambda: self._demo_seat_slots(8, "SEAT"),
            "narrow": lambda: self._demo_seat_slots(8, "SEAT"),
            "jet": lambda: self._demo_seat_slots(3, "SEAT", premium=True),
            "wide": lambda: self._demo_seat_slots(
                6, "SEAT", letters=("A", "B", "C", "D")
            ),
            "ship": lambda: self._demo_bay_slots(6),
            "cabin": lambda: self._demo_seat_slots(
                5, "CABIN", length=1.6, width=1.0, height=2.0, pitch=2.0
            ),
        }
        builder = builders.get(self._demo_space_kind())
        return builder() if builder else []

    def _demo_prepare_model(self):
        """Give the dry van a box long enough for its pallet rows."""
        self.ensure_one()
        if self._demo_space_kind() != "dry_van":
            return
        meter = self.env.ref("uom.product_uom_meter")
        if not self.loading_length:
            self.loading_length = 16.15
            self.loading_length_uom_id = meter
        if not self.door_width:
            self.door_width = 2.5
        if not self.door_height:
            self.door_height = 2.7
        if not self.door_dimension_uom_id:
            self.door_dimension_uom_id = meter

    def _demo_zone(self, index, count):
        if index <= 2:
            return "front"
        if index > count - 2:
            return "rear"
        return "center"

    def _demo_slot(
        self, code, zone, premium, pos_x, pos_y, pos_z, length, width, height
    ):
        return {
            "code": code,
            "zone": zone,
            "is_premium": premium,
            "pos_x": pos_x,
            "pos_y": pos_y,
            "pos_z": pos_z,
            "size_length": length,
            "size_width": width,
            "size_height": height,
        }

    def _demo_pallet_slots(self, rows, top_rows=0):
        length, width, height, gap = 1.2, 1.05, 1.2, 0.12
        sides = (("LEFT", 0.1), ("RIGHT", 1.25))
        slots = []
        for index in range(1, rows + 1):
            pos_x = (index - 1) * (length + gap)
            zone = self._demo_zone(index, rows)
            for side, pos_y in sides:
                slots.append(
                    self._demo_slot(
                        f"ROW-{index:02d}-{side}",
                        zone,
                        index == 1,
                        pos_x,
                        pos_y,
                        0.0,
                        length,
                        width,
                        height,
                    )
                )
                if index <= top_rows:
                    slots.append(
                        self._demo_slot(
                            f"ROW-{index:02d}-{side}-TOP",
                            zone,
                            False,
                            pos_x,
                            pos_y,
                            height,
                            length,
                            width,
                            height,
                        )
                    )
        return slots

    def _demo_seat_slots(
        self,
        rows,
        prefix,
        letters=("A", "B"),
        length=0.55,
        width=0.7,
        height=1.0,
        pitch=0.85,
        premium=False,
    ):
        if len(letters) == 2:
            positions = (0.15, 1.55)
        else:
            positions = (0.05, 0.6, 1.25, 1.85)
            width = 0.5
        slots = []
        for index in range(1, rows + 1):
            pos_x = 0.4 + (index - 1) * pitch
            zone = self._demo_zone(index, rows)
            for letter, pos_y in zip(letters, positions, strict=True):
                slots.append(
                    self._demo_slot(
                        f"{prefix}-{index:02d}-{letter}",
                        zone,
                        premium or index == 1,
                        pos_x,
                        pos_y,
                        0.0,
                        length,
                        width,
                        height,
                    )
                )
        return slots

    def _demo_bay_slots(self, rows):
        length, width, height, pitch = 1.8, 1.0, 2.4, 2.0
        sides = (("PORT", 0.1), ("STBD", 1.3))
        slots = []
        for index in range(1, rows + 1):
            pos_x = (index - 1) * pitch
            zone = self._demo_zone(index, rows)
            for side, pos_y in sides:
                slots.append(
                    self._demo_slot(
                        f"BAY-{index:02d}-{side}",
                        zone,
                        index == 1,
                        pos_x,
                        pos_y,
                        0.0,
                        length,
                        width,
                        height,
                    )
                )
        return slots

    @api.model
    def _demo_models_without_spaces(self):
        """Catalog and dry-van models that still have an empty layout."""
        data = self.env["ir.model.data"].search(
            [
                ("module", "=", "tms"),
                ("model", "=", "fleet.vehicle.model"),
                "|",
                ("name", "=like", "model_%"),
                ("name", "=", "demo_model_dry_van"),
            ]
        )
        models = self.browse(data.mapped("res_id")).exists()
        return models.filtered(lambda model: not model.space_ids)

    @api.model
    def _demo_ensure_spaces(self):
        """Add a layout to every demo model that has none, then sync vehicles."""
        space_model = self.env["tms.vehicle.model.space"]
        for model in self._demo_models_without_spaces():
            model._demo_prepare_model()
            slots = model._demo_space_slots()
            if not slots:
                continue
            space_model.create([dict(slot, model_id=model.id) for slot in slots])
        self._demo_sync_vehicle_spaces()

    @api.model
    def _demo_sync_vehicle_spaces(self):
        """Create the vehicle slot for every model space that is still missing."""
        models = self.env["tms.vehicle.model.space"].search([]).model_id
        vehicles = self.env["fleet.vehicle"].search([("model_id", "in", models.ids)])
        vehicles._sync_model_spaces()
