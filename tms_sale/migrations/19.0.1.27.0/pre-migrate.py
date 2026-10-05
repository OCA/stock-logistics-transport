# Copyright (C) 2026 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def migrate(cr, version):
    """Drop the vehicle TMS service view before its fields are removed."""
    if not version:
        return
    cr.execute(
        """
        DELETE FROM ir_ui_view
         WHERE id IN (
                SELECT res_id
                  FROM ir_model_data
                 WHERE module = 'tms_sale'
                   AND name = 'fleet_vehicle_view_form_tms_sale'
                   AND model = 'ir.ui.view'
               )
        """
    )
    cr.execute(
        """
        DELETE FROM ir_model_data
         WHERE module = 'tms_sale'
           AND name = 'fleet_vehicle_view_form_tms_sale'
           AND model = 'ir.ui.view'
        """
    )
