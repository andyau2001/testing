# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AbkXeroTrackingCategory(models.Model):
    _name = 'abk.xero.tracking.category'
    _description = 'Mapping Xero Tracking Category'
    _rec_name = 'ofield'

    ofield = fields.Char(string='Invoice Field', required=True)
    xero_category_id = fields.Char(string='Xero Category ID', required=True)
    xero_category_option_ids = fields.One2many('abk.xero.tracking.category.option', 'category_id',
                                               string='Xero Category Option IDs', copy=True, auto_join=True)

    def get_xero_mapping(self, ofield, ovalue=None):
        o_id = None
        tracking_category_id = None
        tracking_category_option_id = None

        tracking_category = self.search([('ofield', '=', ofield)], limit=1)
        if tracking_category:
            o_id = tracking_category.id
            tracking_category_id = tracking_category.xero_category_id
            if ovalue:
                tracking_option_ids = tracking_category.xero_category_option_ids
                for tracking_option_id in tracking_option_ids:
                    if tracking_option_id.ovalue == ovalue:
                        tracking_category_option_id = tracking_option_id.xero_category_option_id
                        break

        return {
            "o_category_id": o_id,
            "category_id": tracking_category_id,
            "option_id": tracking_category_option_id
        }


class AbkXeroTrackingCategoryOption(models.Model):
    _name = 'abk.xero.tracking.category.option'
    _description = 'Mapping Xero Tracking Category Option'
    _rec_name = 'ovalue'

    category_id = fields.Many2one('abk.xero.tracking.category', string='Category')
    ovalue = fields.Char(string='Invoice Field Value', required=True)
    xero_category_option_id = fields.Char(string='Xero Category Option ID', required=True)
