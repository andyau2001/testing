# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    product_bundle_ids = fields.One2many(comodel_name='product.bundle', inverse_name='product_template_model', string='Product bundle')
    discount = fields.Float(string='Discount(%)')
    is_bundle = fields.Boolean(string='Is Bundle')
    calculate_bundle_price = fields.Boolean(string='Calculate Bundle Price')

    @api.onchange('is_bundle')
    def remove_variants(self):
        for rec in self:
            if rec.is_bundle:
                rec.attribute_line_ids = False
            else:
                rec.discount = 0

    @api.depends('calculate_bundle_price', 'product_bundle_ids', 'discount')
    @api.onchange('calculate_bundle_price', 'product_bundle_ids', 'discount')
    def get_calculate_bundle_price(self):
        for rec in self:
            if rec.calculate_bundle_price:
                price = 0
                cost = 0
                for one_prd in rec.product_bundle_ids:
                    # price += one_prd.product_qty * one_prd.product_id.lst_price
                    price += one_prd.price_total
                    cost += one_prd.cost * one_prd.product_qty

                price = price - (((price or 0.00) * rec.discount) / 100)
                rec.list_price = price
                rec.standard_price = cost

    def get_calculate_update_price(self):
        for rec in self:
            if rec.calculate_bundle_price and rec.id:
                price = 0
                for one_prd in rec.product_bundle_ids:
                    # price += one_prd.product_qty * one_prd.product_id.lst_price
                    price += one_prd.price_total

                price = price - (((price or 0.00) * rec.discount) / 100)
                # rec.list_price = price
                # rec.sudo().write({'list_price': price})
                self._cr.execute('UPDATE product_template SET list_price = %s WHERE id = %s',(str(price), rec.id))

    @api.model
    def create(self,vals):
        res = super(ProductTemplate,self).create(vals)
        if res.calculate_bundle_price:
            if 'product_bundle_ids' in vals or 'calculate_bundle_price' in vals or 'discount' in vals:
                res.get_calculate_bundle_price()
        return res

    def write(self,vals):
        res = super(ProductTemplate, self).write(vals)
        for rec in self:
            if rec.calculate_bundle_price:
                if 'product_bundle_ids' in vals or 'calculate_bundle_price' in vals or 'discount' in vals:
                    rec.get_calculate_bundle_price()
        return res
