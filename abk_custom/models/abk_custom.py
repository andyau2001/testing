# -*- coding: utf-8 -*-

from odoo import models, api, fields

import logging

_logger = logging.getLogger(__name__)

class CustomPurchaseSaleOrder(models.Model):
    _name = 'purchase.order'
    _inherit = 'purchase.order'
    
    state = fields.Selection([('draft', 'MR'), ('sent', 'MR Sent'), ('to approve', 'To Approve'), ('purchase', 'Purchase Order'), ('done', 'Locked'), ('cancel', 'Cancelled')], 'Status') 