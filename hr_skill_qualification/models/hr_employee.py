# -*- coding: utf-8 -*-

from odoo import models

import logging

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def send_email_to_template(self, em_id):
        if not self.work_email:
            return False
        request_template = self.env['mail.template'].search([('id', '=', int(em_id))], limit=1)
        if request_template:
            mail_ids = []
            email_values = {
                'email_to': self.work_email
            }
            mail_ids.append(request_template.send_mail(self.id, email_values=email_values))

            if mail_ids:
                res = self.env['mail.mail'].browse(mail_ids).send()
        return True
