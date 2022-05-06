# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _

class pos_config(models.Model):
	_inherit = 'pos.config'

	bundle_print = fields.Selection([('only_bundle', "Print only Bundle Product on Receipt"), ('with_products', "Print bundle and bundle item both on receipt")], string='Bundle Print Type', default='with_products')


class pos_order(models.Model):
	_inherit = 'pos.order'


	def create_picking(self):
		"""Create a picking for each order and validate it."""
		Picking = self.env['stock.picking']
		Move = self.env['stock.move']
		StockWarehouse = self.env['stock.warehouse']
		for order in self:
			if not order.lines.filtered(lambda l: l.product_id.type in ['product', 'consu']):
				continue
			address = order.partner_id.address_get(['delivery']) or {}
			picking_type = order.picking_type_id
			return_pick_type = order.picking_type_id.return_picking_type_id or order.picking_type_id
			order_picking = Picking
			return_picking = Picking
			moves = Move
			location_id = picking_type.default_location_src_id.id
			if order.partner_id:
				destination_id = order.partner_id.property_stock_customer.id
			else:
				if (not picking_type) or (not picking_type.default_location_dest_id):
					customerloc, supplierloc = StockWarehouse._get_partner_locations()
					destination_id = customerloc.id
				else:
					destination_id = picking_type.default_location_dest_id.id

			if picking_type:
				pos_qty = all([x.qty >= 0 for x in order.lines])
				picking_id = Picking.create({
					'origin': order.name,
					'partner_id': address.get('delivery', False),
					'date_done': order.date_order,
					'picking_type_id': picking_type.id,
					'company_id': order.company_id.id,
					'move_type': 'direct',
					'note': order.note or "",
					'location_id': location_id if pos_qty else destination_id,
					'location_dest_id': destination_id if pos_qty else location_id,
				})
				message = _("This transfer has been created from the point of sale session: <a href=# data-oe-model=pos.order data-oe-id=%d>%s</a>") % (order.id, order.name)
				picking_id.message_post(body=message)
				order.write({'picking_id': picking_id.id})

			for line in order.lines.filtered(lambda l: l.product_id.type in ['product', 'consu']):
				if line.product_id.pack_ids:
					for item in line.product_id.pack_ids:
						Move +=Move.create({
							 'name': item.name,
							'product_uom': item.product_id.uom_id.id,
							'picking_id': picking_id and picking_id.id or False,
							'picking_type_id': picking_type.id, 
							'product_id': item.product_id.id,
							'product_uom_qty': abs(item.qty_uom) * line.qty,
							'state': 'draft',
							'location_id': location_id if item.qty_uom >= 0 else destination_id,
							'location_dest_id': destination_id if item.qty_uom >= 0 else location_id,
						 })
				else:
					Move += Move.create({
					'name': line.name,
					'product_uom': line.product_id.uom_id.id,
					'picking_id': picking_id and picking_id.id or False,
					'picking_type_id': picking_type.id,
					'product_id': line.product_id.id,
					'product_uom_qty': abs(line.qty),
					'state': 'draft',
					'location_id': location_id if line.qty >= 0 else destination_id,
					'location_dest_id': destination_id if line.qty >= 0 else location_id,
				})
			if picking_id:
				picking_id.action_confirm()
				picking_id.action_assign()
				order.set_pack_operation_lot()
				picking_id.action_done()
			elif Move:
				Move.action_confirm()
				Move.action_assign()
				Move.action_done()
		return True
		

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
