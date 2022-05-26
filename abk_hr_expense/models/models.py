# -*- coding: utf-8 -*-

from odoo import models, fields, _
from odoo.exceptions import UserError

import logging

from datetime import datetime, date

_logger = logging.getLogger(__name__)


class ExpenseResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    expense_amount_over = fields.Float(string='Expense Amount Over', store=True,
                                       config_parameter="hr_expense.expense_amount_over")
    expense_date_over = fields.Integer(string='Expense Amount Over', store=True,
                                       config_parameter="hr_expense.expense_date_over")
    expense_reject_status = fields.Selection([
        ('draft', 'To Submit'),
        ('reported', 'Submitted'),
        ('approved', 'Approved'),
        ('done', 'Paid'),
        ('refused', 'Refused'),
        ('auto_rejected', 'Auto Rejected')
    ], string='Expense Amount Over Status', store=True,
        config_parameter="hr_expense.expense_reject_status")


class AbkHrExpenseAuto(models.Model):
    _inherit = 'hr.expense'

    state = fields.Selection([
        ('draft', 'To Submit'),
        ('reported', 'Submitted'),
        ('approved', 'Approved'),
        ('done', 'Paid'),
        ('refused', 'Refused'),
        ('auto_rejected', 'Auto Rejected')
    ], compute='_compute_state', string='Status', copy=False, index=True, readonly=True, store=True, default='draft',
        help="Status of the expense.")

    project_code = fields.Selection(selection='_auto_get_project_codes', string="Project Code", store=True)

    def days_between(self, d1, d2):
        d1 = datetime.strptime(d1, "%Y-%m-%d")
        d2 = datetime.strptime(d2, "%Y-%m-%d")
        return abs((d2 - d1).days)

    def auto_check_expense_state(self):
        expense_amount_over = self.env['ir.config_parameter'].sudo().get_param('hr_expense.expense_amount_over') or 0
        expense_date_over = self.env['ir.config_parameter'].sudo().get_param('hr_expense.expense_date_over') or 0
        expense_reject_status = self.env['ir.config_parameter'].sudo().get_param(
            'hr_expense.expense_reject_status') or 'auto_rejected'

        expenses = self.search([('state', '=', 'draft')])

        today = date.today()
        d2 = today.strftime("%Y-%m-%d")

        reported = {}

        for expense in expenses:
            if 0 < float(expense_amount_over) <= float(expense.unit_amount):
                expense.update({'state': expense_reject_status})
            elif expense.date and 0 < int(expense_date_over) <= int(
                    self.days_between(expense.date.strftime("%Y-%m-%d"), d2)):
                expense.update({'state': expense_reject_status})
            else:
                if str(expense.employee_id.id) not in reported:
                    reported[str(expense.employee_id.id)] = []
                reported[str(expense.employee_id.id)].append(expense.id)

        self.auto_submit_expenses(reported)

    def auto_submit_expenses(self, reported):
        for employee_id in reported:
            sheet = self._auto_create_sheet_from_expenses(reported[employee_id])
            sheet.action_submit_sheet()

    def _auto_create_sheet_from_expenses(self, expense_ids):
        today = date.today()
        expenses = self.search([('id', 'in', expense_ids)])
        todo = expenses.filtered(lambda x: x.payment_mode == 'own_account') or expenses.filtered(
            lambda x: x.payment_mode == 'company_account')
        sheet = self.env['hr.expense.sheet'].create({
            'company_id': expenses[0].company_id.id,
            'employee_id': expenses[0].employee_id.id,
            'name': 'Auto created ' + today.strftime("%Y-%m-%d"),
            'expense_line_ids': [(6, 0, todo.ids)]
        })
        return sheet

    def _auto_get_project_codes(self):
        lst = []

        employee_rec = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        #department_id = employee_rec and employee_rec.department_id and employee_rec.department_id.id or None
        departments = employee_rec and employee_rec.x_studio_expense_departments or None
        department_ids = []
        if departments is not None:
            for department in departments:
                department_ids.append(department.id)

        sale_orders = self.env['sale.order'].sudo().read_group(
            [('project_code', '!=', ''), ('project_code', '!=', None), ('department', 'in', department_ids)],
            ['project_code'],
            ['project_code'])

        for sale_order in sale_orders:
            lst.append((sale_order.get('project_code'), sale_order.get('project_code')))

        return lst

    def approve_expense_sheets(self):
        self.ensure_one()
        _logger.warning('approve_expense_sheets/approve_expense_sheets/approve_expense_sheets/approve_expense_sheets')
        if not self.user_has_groups('hr_expense.group_hr_expense_team_approver'):
            raise UserError(_("Only Managers and HR Officers can approve expenses"))
        elif not self.user_has_groups('hr_expense.group_hr_expense_manager'):
            current_managers = self.employee_id.expense_manager_id | self.employee_id.parent_id.user_id | self.employee_id.department_id.manager_id.user_id

            # if self.employee_id.user_id == self.env.user:
            #     raise UserError(_("You cannot approve your own expenses"))

            if not self.env.user in current_managers and not self.user_has_groups(
                    'hr_expense.group_hr_expense_user') and self.employee_id.expense_manager_id != self.env.user:
                raise UserError(_("You can only approve your department expenses"))

        notification = {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('There are no expense reports to approve.'),
                'type': 'warning',
                'sticky': False,  # True/False will display for few seconds if false
            },
        }
        filtered_sheet = self.filtered(lambda s: s.state in ['submit', 'draft'])
        if not filtered_sheet:
            return notification
        for sheet in filtered_sheet:
            sheet.write({'state': 'approve', 'user_id': sheet.user_id.id or self.env.user.id})
        notification['params'].update({
            'title': _('The expense reports were successfully approved.'),
            'type': 'success',
            'next': {'type': 'ir.actions.act_window_close'},
        })

        self.activity_update()
        return notification


class AbkHrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    xero_invoice_id = fields.Char(string='Xero ID', required=False)

    def _check_can_approve(self):
        self.ensure_one()
        _logger.warning(
            '_check_can_approve/_check_can_approve/_check_can_approve/_check_can_approve/_check_can_approve')
        if not self.user_has_groups('hr_expense.group_hr_expense_team_approver'):
            raise UserError(_("Only Managers and HR Officers can approve expenses"))
        elif not self.user_has_groups('hr_expense.group_hr_expense_manager'):
            current_managers = self.employee_id.expense_manager_id | self.employee_id.parent_id.user_id | self.employee_id.department_id.manager_id.user_id

            # if self.employee_id.user_id == self.env.user:
            #     raise UserError(_("You cannot approve your own expenses"))

            if not self.env.user in current_managers and not self.user_has_groups(
                    'hr_expense.group_hr_expense_user') and self.employee_id.expense_manager_id != self.env.user:
                raise UserError(_("You can only approve your department expenses"))

    def _do_approve(self):
        self._check_can_approve()

        notification = {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('There are no expense reports to approve.'),
                'type': 'warning',
                'sticky': False,  # True/False will display for few seconds if false
            },
        }

        filtered_sheet = self.filtered(lambda s: s.state in ['submit', 'draft'])
        if not filtered_sheet:
            return notification
        for sheet in filtered_sheet:
            sheet.write({'state': 'approve', 'user_id': sheet.user_id.id or self.env.user.id})
        notification['params'].update({
            'title': _('The expense reports were successfully approved.'),
            'type': 'success',
            'next': {'type': 'ir.actions.act_window_close'},
        })

        self.activity_update()
        return notification

    def approve_expense_sheets(self):
        try:
            return super(AbkHrExpenseSheet, self).approve_expense_sheets()
        except:
            self._do_approve()


class AbkHrExpenseAutoSaleOrder(models.Model):
    _inherit = 'sale.order'

    project_code = fields.Char(string='Project Code', store=True)

    department = fields.Selection(selection='_auto_get_departments', string="Department", store=True, required=True)

    _logger.info('===============================')
    _logger.info(department)

    def _auto_get_departments(self):
        lst = []

        departments = self.env['hr.department'].sudo().search([('company_id', '=', self.env.company.id)])
        for department in departments:
            lst.append((str(department.id), department.name))
        return lst
