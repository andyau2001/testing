# -*- coding: utf-8 -*-
from odoo import http


class AbkCustom(http.Controller):
    @http.route('/abk-custom/export-ir56e-form/')
    def index(self, **kw):
        employee_id = kw.get('employee_id')
        if not employee_id:
            return 'ERROR employee_id'

        employee = http.request.env['hr.employee'].search([('id', '=', int(employee_id))], limit=1)
        if not employee:
            return 'ERROR employee'

        return 'Export IR56E Form. employee: ' + str(employee.name)
