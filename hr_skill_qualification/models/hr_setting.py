# -*- coding: utf-8 -*-

from odoo import models, fields


class HrResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    cert_expired_em_id = fields.Many2one('mail.template',
                                         string='Email Template',
                                         ondelete='set null',
                                         help='This field contains the template that will be used.',
                                         store=True,
                                         config_parameter='employee.certification.cert_expired_em_id')
    cert_expired_days = fields.Char(string='Alert Days',
                                    store=True,
                                    config_parameter='employee.certification.cert_expired_days')
