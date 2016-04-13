# -*- coding: utf-8 -*-
# © initOS GmbH 2016
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import api, models


class stock_picking(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    def open_email_template_wizard(self):
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data.get_object_reference('stock_picking_email',
                                                             'email_template_tracking')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail',
                                                                 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update({
            'default_model': 'stock.picking',
            'default_res_id': self._ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
        })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    def send_tracking_email(self):
        assert len(self._ids) == 1, 'This option should only be used for a single id at a time.'
        return self.open_email_template_wizard()
