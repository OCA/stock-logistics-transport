# Copyright 2024 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import models


class ShipmentAdvice(models.Model):
    _inherit = "shipment.advice"

    def button_plan_reception(self):
        action_xmlid = (
            "shipment_advice_reception_planner.wizard_plan_reception_shipment_action"
        )
        return self.env["ir.actions.actions"]._for_xml_id(action_xmlid)

    def write(self, vals):
        res = super().write(vals)
        if "arrival_date" in vals.keys():
            # Update the scheduled date on the planned moves
            incoming_shipment = self.filtered(
                lambda shipment: shipment.shipment_type == "incoming"
                and shipment.state not in ("done", "cancel")
            )
            if incoming_shipment:
                incoming_shipment.planned_move_ids.write({"date": vals["arrival_date"]})
        return res
