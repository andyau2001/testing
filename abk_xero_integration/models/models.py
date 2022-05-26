# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AbkXeroIntegration(models.Model):
    _name = 'abk.xero.integration'
    _description = 'ABK Xero Integration'

    name = fields.Char(string='Name', required=True)

    xero_type = fields.Char(string='Xero Type', required=True, default='Invoices')
    xero_id = fields.Char(string='Xero ID', required=True)
    odoo_model = fields.Char(string='Odoo Model', required=True, default='account.move')
    odoo_id = fields.Char(string='Odoo ID', required=True)

    date_integrated = fields.Datetime(string='Date Integrated', default=fields.Datetime.now())


class AbkXeroResPartner(models.Model):
    _description = 'ABK Xero Contact'
    _inherit = 'res.partner'

    xero_contact_id = fields.Char(string='Xero ID', required=False)
    xero_contact_number = fields.Char(string='Xero Number', required=False)

    def find_xero(self, xero_contact_id):
        try:
            return self.search(['xero_contact_id', '=', xero_contact_id], limit=1)
        except:
            return None


class AbkXeroProductTemplate(models.Model):
    _description = 'ABK Xero Product Template'
    _inherit = 'product.template'

    xero_item_id = fields.Char(string='Xero ID', required=False)


class AbkXeroPurchaseOrder(models.Model):
    _description = 'AbkXeroPurchaseOrder'
    _inherit = 'purchase.order'

    xero_po_id = fields.Char(string='Xero ID', required=False)


class AbkXeroInvoicing(models.Model):
    _description = 'AbkXeroInvoicing'
    _inherit = 'account.move'

    xero_invoice_id = fields.Char(string='Xero ID', required=False)


class AbkXeroEmployee(models.Model):
    _description = 'AbkXeroEmployee'
    _inherit = 'hr.employee'

    xero_contact_id = fields.Char(string='Xero ID', required=False)
