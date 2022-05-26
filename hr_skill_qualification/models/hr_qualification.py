# -*- coding: utf-8 -*-
# Part of Odoo, Aktiv Software PVT. LTD.
# See LICENSE file for full copyright & licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from datetime import date, datetime, timedelta

import logging

_logger = logging.getLogger(__name__)


class EmployeeEducation(models.Model):
    _name = "employee.education"
    _description = "Employee Education"

    applicant_id = fields.Many2one("hr.applicant", "applicant")
    employee_id = fields.Many2one("hr.employee", "Employee")
    type_id = fields.Many2one("hr.recruitment.degree", "Degree", ondelete="cascade")
    institute_id = fields.Many2one("hr.institute", "Institutes", ondelete="cascade")
    score = fields.Char()
    qualified_year = fields.Date()
    doc = fields.Binary("Transcripts")


class HrInstitute(models.Model):
    _name = "hr.institute"
    _description = "Hr Institute"

    name = fields.Char()
    country_id = fields.Many2one("res.country", "Country")
    state_id = fields.Many2one("res.country.state", "State")


class EmployeeCertification(models.Model):
    _name = "employee.certification"
    _description = "Employee Certification"

    applicant_id = fields.Many2one("hr.applicant", "applicant")
    employee_id = fields.Many2one("hr.employee", "Employee")
    course_id = fields.Many2one("cert.cert", "Course Name", ondelete="cascade")
    levels = fields.Char("Bands/Levels of Completion")
    year = fields.Date("Year of completion")
    doc = fields.Binary("Certificates")

    from_date = fields.Date("Start Date")
    to_date = fields.Date("End Date")

    payslip_id = fields.Many2one('hr.payslip', string="Payslip", readonly=True)

    is_expired_remind = fields.Boolean('Expired Remind', default=False)

    def remind_expire_date(self):
        _logger.info('Check Expired Employee Certificate --------------------------------------->')
        cert_expired_em_id = self.env['ir.config_parameter'].sudo().get_param(
            'employee.certification.cert_expired_em_id') or None
        if not cert_expired_em_id:
            return False
        cert_expired_days = self.env['ir.config_parameter'].sudo().get_param(
            'employee.certification.cert_expired_days') or '0'
        days = cert_expired_days.split(',')
        now = datetime.now()
        domains = []
        for x in range(len(days) - 1):
            domains.append('|')
        for d in days:
            day_date = str((now - timedelta(days=int(d))).date())
            domains.append(('to_date', '=', day_date))
        _logger.info(domains)
        certifications = self.search(domains)
        for certification in certifications:
            employee = certification.employee_id
            if employee and employee.work_email:
                res = certification.send_email_to_template(cert_expired_em_id, employee.work_email)
                if res:
                    certification.write({'is_expired_remind': True})
        return True

    def send_email_to_template(self, em_id, email_to):
        request_template = self.env['mail.template'].search([('id', '=', int(em_id))], limit=1)
        if request_template:
            mail_ids = []
            email_values = {
                'email_to': email_to
            }
            mail_ids.append(request_template.send_mail(self.id, email_values=email_values))

            if mail_ids:
                self.env['mail.mail'].browse(mail_ids).send()
                return True
        return False


class CertCert(models.Model):
    _name = "cert.cert"
    _description = "Cert Cert"

    name = fields.Char("Course Name")
    bonus_amount = fields.Float("Bonus Amount")


class EmployeeProfession(models.Model):
    _name = "employee.profession"
    _description = "Employee Profession"

    applicant_id = fields.Many2one("hr.applicant", "applicant")
    employee_id = fields.Many2one("hr.employee", "Employee")
    job_id = fields.Many2one("hr.job", "Job Title")
    location = fields.Char()
    from_date = fields.Date("Start Date")
    to_date = fields.Date("End Date")
    doc = fields.Binary("Experience Certificates")

    _sql_constraints = [
        (
            "to_date_greater",
            "check(to_date > from_date)",
            "Start Date of Professional Experience should be less than End Date!",
        ),
    ]

    @api.constrains("from_date", "to_date")
    def check_from_date(self):
        """
        This method is called when future Start date is entered.
        --------------------------------------------------------
        @param self : object pointer
        """
        today = date.today()
        if (self.from_date > today) or (self.to_date > today):
            raise ValidationError(
                "Future Start Date or End Date in Professional experience is not acceptable!!"
            )
