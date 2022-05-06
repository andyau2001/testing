# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

import json
import logging

_logger = logging.getLogger(__name__)


class PosConfig(models.Model):
    _inherit = 'pos.config'


class CustomPosOrder(models.Model):
    _inherit = 'pos.order'

    pos_order_prefix = fields.Char(string='Prefix', store=True)
    pos_order_date = fields.Date(string='Date', store=True)
    pos_order_remark = fields.Char(string='Remark', store=True)
    pos_order_remark_internal = fields.Char(string='Remark Internal', store=True)

    @api.model
    def _order_fields(self, ui_order):
        _logger.info('_order_fields')
        _logger.info(ui_order)
        fields = super(CustomPosOrder, self)._order_fields(ui_order)
        fields['pos_order_prefix'] = ui_order['pos_order_prefix'] or ''
        fields['pos_order_date'] = ui_order['pos_order_date'] or ''
        fields['pos_order_remark'] = ui_order['pos_order_remark'] or ''
        fields['pos_order_remark_internal'] = ui_order['pos_order_remark_internal'] or ''
        _logger.info('_order_fields')
        _logger.info(fields)
        return fields

    @api.model
    def _process_order(self, order, draft, existing_order):
        _logger.info('_process_order')
        _logger.info(order)
        _logger.info(existing_order)
        return super(CustomPosOrder, self)._process_order(order, draft, existing_order)

    @api.model
    def create(self, values):
        _logger.info('create')
        _logger.info(values)
        return super(CustomPosOrder, self).create(values)

    def action_pos_order_invoice(self):
        moves = self.env['account.move']

        for order in self:
            # Force company for all SUPERUSER_ID action
            if order.account_move:
                moves += order.account_move
                continue

            if not order.partner_id:
                raise UserError(_('Please provide a partner for the sale.'))

            move_vals = order._prepare_invoice_vals()
            _logger.info(order.pos_order_date)
            _logger.info(order.pos_order_remark)
            _logger.info(order.pos_order_remark_internal)
            # @JACKY
            move_vals['invoice_date'] = order.pos_order_date
            move_vals['x_studio_remark_c'] = order.pos_order_remark
            move_vals['x_studio_remark_internal_used_only'] = order.pos_order_remark_internal
            _logger.info(move_vals)
            new_move = order._create_invoice(move_vals)
            _logger.info(new_move)
            order.write({'account_move': new_move.id, 'state': 'invoiced'})
            new_move.sudo().with_company(order.company_id)._post()
            moves += new_move

        if not moves:
            return {}

        return {
            'name': _('Customer Invoice'),
            'view_mode': 'form',
            'view_id': self.env.ref('account.view_move_form').id,
            'res_model': 'account.move',
            'context': "{'move_type':'out_invoice'}",
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': moves and moves.ids[0] or False,
        }


class CustomPosInvoice(models.Model):
    _inherit = 'account.move'

    invoice_prefix = fields.Selection(selection=[('R', 'R'), ('HLL', 'HLL'), ('CMHA', 'CMHA'), ('CM', 'CM')],
                                      string="Invoice Prefix", store=True, required=False, readonly=False,
                                      compute="_compute_prefix")

    @api.depends('pos_order_ids.pos_order_prefix')
    def _compute_prefix(self):
        for record in self:
            record['invoice_prefix'] = record.pos_order_ids.pos_order_prefix

    @api.model
    def get_all_prefix(self):
        selection = dict(self._fields['invoice_prefix'].selection)
        return json.dumps(selection)

    x_studio_remark = fields.Char(string='Description', stored=True, readonly=False,indexed=True)