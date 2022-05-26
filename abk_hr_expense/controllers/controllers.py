# -*- coding: utf-8 -*-
# from odoo import http


# class AbkHrExpense(http.Controller):
#     @http.route('/abk_hr_expense/abk_hr_expense/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/abk_hr_expense/abk_hr_expense/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('abk_hr_expense.listing', {
#             'root': '/abk_hr_expense/abk_hr_expense',
#             'objects': http.request.env['abk_hr_expense.abk_hr_expense'].search([]),
#         })

#     @http.route('/abk_hr_expense/abk_hr_expense/objects/<model("abk_hr_expense.abk_hr_expense"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('abk_hr_expense.object', {
#             'object': obj
#         })
