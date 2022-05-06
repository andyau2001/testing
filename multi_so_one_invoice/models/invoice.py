# -*- coding: utf-8 -*-
# This module and its content is copyright of Technaureus Info Solutions Pvt. Ltd.
# - © Technaureus Info Solutions Pvt. Ltd 2020. All rights reserved.

from odoo import api, fields, models
from odoo.tools.float_utils import float_compare


class AccountMove(models.Model):
    _inherit = 'account.move'

    multi_so = fields.Boolean(string='Multiple Sales Order', default=False)
    sale_id = fields.Many2one('sale.order', string='Add Sales Order',
                              help='Encoding help. When selected, the associated sales order lines are added to '
                                   'the customer invoice. Several SO can be selected.')

    @api.onchange('multi_so')
    def _onchange_multi_so(self):
        self.invoice_line_ids = ()
        self.line_ids = ()
        return self._onchange_allowed_sale_ids()

    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        if self.multi_so == True:
            self.invoice_line_ids = ()
            self.line_ids = ()
        return super(AccountMove, self)._onchange_partner_id()

    @api.onchange('state', 'partner_id', 'invoice_line_ids')
    def _onchange_allowed_sale_ids(self):
        '''
        The purpose of the method is to define a domain for the available
        sales orders.
        '''
        result = {}

        so_line_ids = self.invoice_line_ids.mapped('so_line_id')
        sale_ids = self.invoice_line_ids.mapped('sale_id').filtered(lambda r: r.order_line <= so_line_ids)

        result['domain'] = {'sale_id': [
            ('invoice_status', '=', 'to invoice'),
            ('partner_id', 'child_of', self.partner_id.id),
            ('id', 'not in', sale_ids.ids),
        ]}
        return result

    @api.onchange('sale_id')
    def sale_order_change(self):
        if not self.sale_id:
            return {}
        if not self.partner_id:
            self.partner_id = self.sale_id.partner_id.id

        new_lines = self.env['account.move.line']
        vals_list = []
        for line in self.sale_id.order_line:
            if line in self.invoice_line_ids.mapped('so_line_id'):
                continue
            if line.product_id.invoice_policy == 'order':
                qty = line.product_uom_qty - line.qty_invoiced
            else:
                qty = line.qty_delivered - line.qty_invoiced
            if qty and float_compare(qty, 0.0, precision_rounding=line.product_uom.rounding) <= 0:
                qty = 0.0
            taxes = line.tax_id
            invoice_line_tax_ids = line.order_id.fiscal_position_id.map_tax(taxes)

            account = line.product_id.property_account_income_id or line.product_id.categ_id.property_account_income_categ_id
            fpos = line.order_id.fiscal_position_id or line.order_id.partner_id.property_account_position_id
            if fpos:
                account = fpos.map_account(account)
            price_unit = line.order_id.currency_id.compute(line.price_unit, self.currency_id, round=False)
            price_unit_wo_discount = price_unit * (1 - (line.discount / 100.0))
            subtotal = qty * price_unit_wo_discount

            if taxes:
                taxes_res = taxes._origin.compute_all(price_unit_wo_discount,
                                                      quantity=qty, currency=self.currency_id, product=line.product_id,
                                                      partner=self.partner_id,
                                                      is_refund=self.type in ('out_refund', 'in_refund'))
                price_subtotal = taxes_res['total_excluded']
            else:
                price_subtotal = subtotal

            data = {
                'so_line_id': line.id,
                'name': line.name,
                'sequence': line.sequence,
                'product_uom_id': line.product_uom.id,
                'product_id': line.product_id.id or False,
                'account_id': account.id,
                'debit': 0.0,
                'credit': price_subtotal,
                'price_unit': line.order_id.currency_id.compute(line.price_unit, self.currency_id, round=False),
                'quantity': qty,
                'discount': line.discount,
                'analytic_account_id': line.order_id and line.order_id.analytic_account_id.id,
                'tax_ids': invoice_line_tax_ids.ids,
                'display_type': line.display_type,
                'price_subtotal': price_subtotal
            }
            vals_list.append(data)
            new_line = new_lines.new(data)
            new_lines += new_line

        self.invoice_line_ids += new_lines
        self.line_ids += new_lines
        self._recompute_tax_lines()
        self._recompute_dynamic_lines()
        self.sale_id = False
        sale_ids = self.invoice_line_ids.mapped('sale_id')
        if sale_ids:
            self.invoice_origin = ', '.join(sale_ids.mapped('name'))
        return {}

    @api.onchange('currency_id')
    def _onchange_currency_id(self):
        if self.currency_id:
            for line in self.invoice_line_ids.filtered(lambda r: r.so_line_id):
                line.price_unit = line.sale_id.currency_id.compute(line.so_line_id.price_unit, self.currency_id,
                                                                   round=False)


class AccountMoveLine(models.Model):
    """ Override AccountInvoice_line to add the link to the sales order line it is related to"""
    _inherit = 'account.move.line'

    so_line_id = fields.Many2one('sale.order.line', 'Sales Order Line', ondelete='set null', select=True,
                                 readonly=False)
    sale_id = fields.Many2one('sale.order', related='so_line_id.order_id', string='Sales Order', store=False,
                              readonly=False,
                              help='Associated Sales Order. Filled in automatically when a SO is chosen on the vendor bill.')

    @api.model_create_multi
    def create(self, vals):
        if vals:
            for val in vals:
                if val.get('so_line_id', False):
                    val.update({'sale_line_ids': [(6, 0, [val.get('so_line_id')])]})
        return super(AccountMoveLine, self).create(vals)
