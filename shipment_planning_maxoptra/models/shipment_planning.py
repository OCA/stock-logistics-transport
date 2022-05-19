# Copyright 2022 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
import base64
import io

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools import pycompat

from ..const import MAXOPTRA_COLUMN_NAMES, MAXOPTRA_DATE_FORMAT


class ShipmentPlanning(models.Model):

    _inherit = "shipment.planning"

    maxoptra_planning = fields.Boolean(
        help="When marked, the 'In Progress' action will generate a CSV file "
        "to be imported on MaxOptra",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    maxoptra_to_import_file = fields.Binary(attachment=True, readonly=True)
    maxoptra_to_import_file_name = fields.Char(readonly=True)
    maxoptra_exported_file = fields.Binary(attachment=True, readonly=True)
    maxoptra_exported_file_name = fields.Char(readonly=True)

    batch_picking_ids = fields.One2many("stock.picking.batch", "shipment_planning_id")

    def action_in_progress(self):
        res = super().action_in_progress()
        for planning in self:
            if planning.maxoptra_planning:
                # TODO: Use with_delay to generate CSV through queue job?
                planning.generate_csv()
        return res

    def action_done(self):
        # TODO: Restrict action if CSV wasn't generated
        return super().action_done()

    def action_import_maxoptra_schedule(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "shipment.maxoptra.schedule.import",
            "target": "new",
            "view_mode": "form",
            "context": {"active_id": self.id, "active_model": self._name},
        }

    def generate_csv(self):
        self.ensure_one()
        csv_result = self._create_csv()
        self.write(
            {
                "maxoptra_to_import_file": base64.b64encode(csv_result),
                "maxoptra_to_import_file_name": self.name.replace("/", "_") + ".csv",
            }
        )
        return True

    def _create_csv(self):
        buff = io.BytesIO()
        writer = pycompat.csv_writer(buff, quoting=1)

        writer.writerow(self.get_header_names())

        for pick in self.picking_to_plan_ids:
            row = self.prepare_row(pick)
            writer.writerow(row)
        csv_value = buff.getvalue()
        buff.close()
        return csv_value

    def prepare_row(self, pick):
        # TODO: prefetch warehouses before the loop to avoid calling this
        #  search on each iteration?
        wh = pick.location_id.get_warehouse()
        if not wh.maxoptra_distribution_centre_name:
            raise UserError(
                _("Please define MaxOptra Distribution Centre Name on Warehouse %s")
                % wh.name
            )
        partner_address = pick.partner_id._get_maxoptra_address()
        return [
            pick.name,
            pick.scheduled_date.strftime(MAXOPTRA_DATE_FORMAT),
            wh.maxoptra_distribution_centre_name,
            pick.partner_id.name,
            pick.partner_id.phone or "",
            pick.partner_id.email or "",
            partner_address,
            pick.partner_id.maxoptra_partner_key or "",
        ]

    def get_header_names(self):
        return MAXOPTRA_COLUMN_NAMES
