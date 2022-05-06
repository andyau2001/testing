# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class product_bundle_wizard(models.TransientModel):
    _name = 'product.bundle.wizard'

    product_bundle_id = fields.Many2one('product.product', string='Bundle', required=True, domain="[('is_bundle', '=', True)]")
    qty = fields.Integer('Quantity', required=True , default=1)
    price = fields.Float(string="Price")
    product_bundle_ids = fields.One2many('product.bundle', related='product_bundle_id.product_bundle_ids', string="Bundle Products")

    @api.onchange('product_bundle_id')
    def onchange_product_bundle(self):
        if self.product_bundle_id:
            self.price = self.product_bundle_id.lst_price
        else:
            pass

    def add_bundle_in_so(self):
        for rec in self:
            if rec.product_bundle_id.is_bundle:
                self.env['sale.order.line'].create({
                    'order_id': self.env.context.get('active_id'),
                    'product_id': rec.product_bundle_id and rec.product_bundle_id.id,
                    'name': rec.product_bundle_id and rec.product_bundle_id.name,
                    'price_unit': self.price,
                    'product_uom': rec.product_bundle_id and rec.product_bundle_id.uom_id and rec.product_bundle_id.uom_id.id,
                    'product_uom_qty': self.qty
                })
