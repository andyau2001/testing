# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT


class sale_order_line(models.Model):
    _inherit = 'sale.order.line'

    product_bundle_ids = fields.One2many('product.bundle', related='product_id.product_bundle_ids', string="Bundle Products")

    @api.onchange('product_id', 'product_uom_qty')
    def _onchange_product_uom_qty(self):
        res = super(sale_order_line, self)._onchange_product_uom_qty()
        if self.product_id and self.product_id.is_bundle:
            for one_prd in self.product_id.product_bundle_ids:
                if one_prd and one_prd.product_id.type == 'product':
                    precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
                    qty = self.product_uom_qty
                    if qty * one_prd.product_qty > one_prd.product_id.virtual_available:
                        product = one_prd.product_id
                        message = _('You plan to sell %s %s of %s but you only have %s %s available in %s warehouse.') % \
                                  (self.product_uom_qty, self.product_uom.name, product.name, product.virtual_available, product.uom_id.name, self.order_id.warehouse_id.name)
                        if float_compare(product.virtual_available, product.virtual_available, precision_digits=precision) == -1:
                            message += _('\nThere are %s %s available across all warehouses.\n\n') % (product.virtual_available, product.uom_id.name)
                            for warehouse in self.env['stock.warehouse'].search([]):
                                quantity = product.with_context(warehouse=warehouse.id).virtual_available
                                if quantity > 0:
                                    message += "%s: %s %s\n" % (warehouse.name, quantity, product.uom_id.name)
                        return {'warning': {
                            'title': _('Ordered quantity decreased!'),
                            'message' : message
                        }}
        return res

    def _compute_qty_delivered(self):
        super(sale_order_line, self)._compute_qty_delivered()
        for line in self:
            if line.qty_delivered_method == 'stock_move':
                qty_delivered = False
                if line.product_id.is_bundle == True:
                    bundle_products = []
                    for one_prd in line.product_id.product_bundle_ids:
                        bundle_products.append(one_prd.product_id)
                    for move in line.move_ids.filtered(lambda r: r.state == 'done' and not r.scrapped and  r.product_id in bundle_products):
                        if move.state == 'done' and move.product_uom_qty == move.quantity_done:
                            qty_delivered = True
                        else:
                            qty_delivered = False
                            break
                    if qty_delivered:
                        line.qty_delivered = line.product_uom_qty

    def _prepare_procurement_values(self, group_id):
        res = super(sale_order_line, self)._prepare_procurement_values(group_id=group_id)
        date_planned = fields.Datetime.now() + timedelta(days=self.customer_lead or 0.0) - timedelta(days=self.order_id.company_id.security_lead)
        if self.product_id.product_bundle_ids:
            res_list = []
            for one_bundle in self.product_id.product_bundle_ids:
                vals = {
                    'company_id': self.order_id.company_id,
                    'group_id': group_id,
                    'origin': self.order_id.name,
                    'sale_line_id': self.id,
                    'name': one_bundle.product_id.name,
                    'warehouse_id': self.order_id.warehouse_id and self.order_id.warehouse_id,
                    'location_id': self.order_id.partner_shipping_id.property_stock_customer.id,
                    'route_ids': self.route_id,
                    'partner_dest_id': self.order_id.partner_shipping_id,
                    'partner_id': self.order_id.partner_id.id,
                    'product_id': one_bundle.product_id.id,
                    'product_qty': one_bundle.product_qty * abs(self.product_uom_qty),
                    'product_uom': one_bundle.product_uom_id and one_bundle.product_uom_id.id,
                    'date_planned': date_planned,
                }
                for line in self.filtered("order_id.commitment_date"):
                    date_planned = fields.Datetime.from_string(line.order_id.commitment_date) - timedelta(days=line.order_id.company_id.security_lead)
                    vals.update({
                        'date_planned': fields.Datetime.to_string(date_planned),
                    })
                res_list.append(vals)
            return res_list
        return res

    def _action_launch_stock_rule(self, previous_product_uom_qty=False):
        """
        Launch procurement group run method with required/custom fields genrated by a
        sale order line. procurement group will launch '_run_pull', '_run_buy' or '_run_manufacture'
        depending on the sale order line product rule.
        """
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        procurements = []
        errors = []
        for line in self:
            if line.state != 'sale' or not line.product_id.type in ('consu','product'):
                continue
            qty = line._get_qty_procurement(previous_product_uom_qty)
            if float_compare(qty, line.product_uom_qty, precision_digits=precision) >= 0:
                continue

            group_id = line._get_procurement_group()
            if not group_id:
                group_id = self.env['procurement.group'].create(line._prepare_procurement_group_vals())
                line.order_id.procurement_group_id = group_id
            else:
                # In case the procurement group is already created and the order was
                # cancelled, we need to update certain values of the group.
                updated_vals = {}
                if group_id.partner_id != line.order_id.partner_shipping_id:
                    updated_vals.update({'partner_id': line.order_id.partner_shipping_id.id})
                if group_id.move_type != line.order_id.picking_policy:
                    updated_vals.update({'move_type': line.order_id.picking_policy})
                if updated_vals:
                    group_id.write(updated_vals)

            values = line._prepare_procurement_values(group_id=group_id)

            if line.product_id.product_bundle_ids:
                for one_value in values:
                    try:
                        procurements.append(self.env['procurement.group'].Procurement(
                            self.env['product.product'].browse(one_value.get('product_id')),
                            one_value.get('product_qty'), self.env['uom.uom'].browse(one_value.get('product_uom')),
                            line.order_id.partner_shipping_id.property_stock_customer,
                            one_value.get('name'), line.order_id.name, line.order_id.company_id, one_value))
                    except UserError as error:
                        errors.append(error.name)
            else:
                product_qty = line.product_uom_qty - qty
                line_uom = line.product_uom
                quant_uom = line.product_id.uom_id
                product_qty, procurement_uom = line_uom._adjust_uom_quantities(product_qty, quant_uom)
                try:
                    procurements.append(self.env['procurement.group'].Procurement(
                        line.product_id, product_qty, procurement_uom,
                        line.order_id.partner_shipping_id.property_stock_customer,
                        line.name, line.order_id.name, line.order_id.company_id, values))
                except UserError as error:
                    errors.append(error.name)
        if errors:
            raise UserError('\n'.join(errors))

        if procurements:
            self.env['procurement.group'].run(procurements)
        return True
