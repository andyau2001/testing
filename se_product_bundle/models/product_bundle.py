# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ProductBundle(models.Model):
    _name = 'product.bundle'

    product_template_model = fields.Many2one(comodel_name='product.template', string='Product bundle')
    product_id = fields.Many2one(comodel_name='product.product', string='Product', required=True)
    product_qty = fields.Float(string='Quantity', required=True, default=1.0)
    price = fields.Float(related='product_id.lst_price', string='Price')
    cost = fields.Float(related='product_id.standard_price', string='Cost', readonly="1")
    discount = fields.Float(string='Discount(%)')
    product_uom_id = fields.Many2one(related='product_id.uom_id' , string="Unit of Measure", readonly="1")
    name = fields.Char(related='product_id.name', readonly="1")

    @api.depends('product_id', 'product_qty', 'discount', 'product_id.lst_price')
    @api.onchange('product_id', 'product_qty', 'discount', 'product_id.lst_price')
    def _get_total_price(self):
        for rec in self:
            try:
                total_final_price = rec.price * rec.product_qty
                total_final_price = total_final_price - (((total_final_price or 0.00) * rec.discount) / 100)
                rec.price_total = total_final_price
                rec.product_template_model.get_calculate_update_price()
            except:
                continue

    price_total = fields.Float(compute=_get_total_price, string='Total', store=True)
