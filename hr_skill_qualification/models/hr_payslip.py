# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    certification_ids = fields.One2many(
        'employee.certification', 'payslip_id', string='Certification', readonly=False,
        help="certification to reimburse to employee.",
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    certification_count = fields.Integer(compute='_compute_certification_count')

    @api.depends('certification_ids.payslip_id')
    def _compute_certification_count(self):
        for payslip in self:
            payslip.certification_count = len(payslip.mapped('certification_ids.payslip_id'))

    @api.model_create_multi
    def create(self, vals_list):
        payslips = super().create(vals_list)
        # draft_slips = payslips.filtered(lambda p: p.employee_id and p.state == 'draft')
        # if not draft_slips:
        #     return payslips
        # current_date = str(datetime.now().date())
        # certifications = self.env['employee.certification'].search([
        #     ('employee_id', 'in', draft_slips.mapped('employee_id').ids),
        #     ('from_date', '>=', current_date),
        #     ('to_date', '<=', current_date),
        #     ('payslip_id', '=', False)])
        # for slip in draft_slips:
        #     payslip_certifications = certifications.filtered(lambda s: s.employee_id == slip.employee_id)
        #     slip.certification_ids = [(5, 0, 0)] + [(4, s.id, False) for s in payslip_certifications]
        return payslips
