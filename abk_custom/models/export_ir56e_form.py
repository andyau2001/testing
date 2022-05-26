# -*- coding: utf-8 -*-

from odoo import models, api

import logging

_logger = logging.getLogger(__name__)


class ExportIR56EForm(models.Model):
    _inherit = 'hr.employee'

    def action_export_ir56e(self, html=False):
        if html is True:
            return self.env.ref('abk_custom.action_export_ir56e_form_html').report_action(self.ids)
        return self.env.ref('abk_custom.action_export_ir56e_form').report_action(self.ids)

        # return {
        #     'type': 'ir.actions.act_url',
        #     'url': '/abk-custom/export-ir56e-form/?employee_id=' + str(self.ids[0]),
        #     'target': 'self',
        # }
