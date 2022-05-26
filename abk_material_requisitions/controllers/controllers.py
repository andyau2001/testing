# -*- coding: utf-8 -*-
# from odoo import http


# class AbkMaterialRequisitions(http.Controller):
#     @http.route('/abk_material_requisitions/abk_material_requisitions', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/abk_material_requisitions/abk_material_requisitions/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('abk_material_requisitions.listing', {
#             'root': '/abk_material_requisitions/abk_material_requisitions',
#             'objects': http.request.env['abk_material_requisitions.abk_material_requisitions'].search([]),
#         })

#     @http.route('/abk_material_requisitions/abk_material_requisitions/objects/<model("abk_material_requisitions.abk_material_requisitions"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('abk_material_requisitions.object', {
#             'object': obj
#         })
