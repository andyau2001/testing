# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

import urllib3
import json
import logging
import time
import base64

from xero_python.api_client import ApiClient
from xero_python.api_client.configuration import Configuration
from xero_python.api_client.oauth2 import OAuth2Token
from xero_python.accounting import AccountingApi, Contact, Contacts, PurchaseOrder, PurchaseOrders, Phone, LineItem, \
    LineItemTracking, Invoice, Invoices, TrackingOption
from xero_python.exceptions import AccessTokenExpiredError, AccountingBadRequestException

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
_logger = logging.getLogger(__name__)


class AbkXeroSession(models.Model):
    _name = 'abk.xero.session'
    _description = 'ABK Xero Auth Session'

    server = 'https://api.xero.com'

    type = fields.Char(string='Type', required=True, default="Session")

    date_created = fields.Datetime(string='Date Created', default=fields.Datetime.now())
    name = fields.Char(string='Name', required=True, default="{}")
    extra = fields.Text(string='Extra Data', required=False)

    login_url = fields.Char(string='Login URL', required=False)
    client_id = fields.Char(string='Client ID', required=False)
    client_secret = fields.Char(string='Client Secret', required=False)

    def get_xero_config(self):
        try:
            config = self.search([('type', '=', 'Config')])[-1]
        except:
            config = None

        return {
            'login_url': config and config.login_url or None,
            'client_id': config and config.client_id or None,
            'client_secret': config and config.client_secret or None
        }

    def get_xero_session(self):
        try:
            session = self.search([('type', '=', 'Session')])[-1]
        except:
            session = None

        if session:
            token = json.loads(session.name) or {}
            try:
                extra = json.loads(session.extra)
            except:
                extra = {}
            access_token = token.get('access_token', None)
            tenants = extra.get('tenants', [])
            return {
                'access_token': access_token,
                'tenants': tenants,
                'token': token
            }
        return {}

    def get_api_client(self):
        xero_api_config = self.get_xero_config()
        api_client = ApiClient(
            Configuration(
                debug=True,
                oauth2_token=OAuth2Token(
                    client_id=xero_api_config.get('client_id'),
                    client_secret=xero_api_config.get('client_secret')
                ),
            ),
            pool_threads=1,
        )

        @api_client.oauth2_token_getter
        def obtain_xero_oauth2_token():
            session = self.get_xero_session()
            return session.get('token')

        @api_client.oauth2_token_saver
        def store_xero_oauth2_token(token):
            self.update_token(token)

        return api_client

    @api.model
    def save_xero_session(self, auth_res):
        auth_res['expires_at'] = time.time() + int(auth_res.get('expires_in'))
        connections = self.get_xero_connections(auth_res.get('access_token'))
        tenants = []
        for connection in connections:
            tenants.append({
                'tenantId': connection.get('tenantId'),
                'tenantName': connection.get('tenantName')
            })
        extra = {
            'tenants': tenants
        }
        extra = json.dumps(extra)
        token = json.dumps(auth_res)
        vals_list = {'name': token, 'extra': extra}
        return super(AbkXeroSession, self).create(vals_list)

    def update_token(self, new_token):
        new_token['expires_at'] = time.time() + int(new_token.get('expires_in'))
        session = self.search([('type', '=', 'Session')])[-1]
        name = json.dumps(new_token)
        _logger.info(name)
        session.write({'name': name})

    def request(self, uri, method='GET', body='', access_token=''):
        url = self.server + uri
        _logger.info('REQ: --------------------------------------------> ' + url)
        client = urllib3.PoolManager()
        if not access_token:
            session = self.get_xero_session()
            if session:
                access_token = session.get('access_token')
        if access_token:
            headers = {
                'Authorization': 'Bearer ' + access_token,
                'Content-Type': 'application/json'
            }
            res = client.request(method, url, headers=headers)
            data = json.loads(res.data)
            _logger.info('RES: ------------------------------------------------->')
            _logger.info(data)
            return data
        return None

    def refresh_token(self):
        xero_api_config = self.get_xero_config()
        session = self.get_xero_session()
        token = session.get('token')

        url = 'https://identity.xero.com/connect/token'
        client = urllib3.PoolManager()
        basic = xero_api_config.get('client_id') + ':' + xero_api_config.get('client_secret')
        encoded_bytes = base64.b64encode(basic.encode('ascii'))
        encoded = encoded_bytes.decode('ascii')

        headers = {
            'authorization': 'Basic ' + encoded
        }

        body = {
            'grant_type': 'refresh_token',
            'refresh_token': token.get('refresh_token')
        }

        r = client.request('POST', url, fields=body, headers=headers)
        result = json.loads(r.data)
        _logger.info(result)
        if result.get('id_token'):
            self.update_token(result)

    def get_xero_connections(self, access_token):
        data = self.request('/connections', access_token=access_token)
        try:
            status = data.get('Status')
        except:
            status = 200

        if status != 200:
            return {}

        return data


class AbkXeroCompany(models.Model):
    _description = 'ABK Xero Company'
    _inherit = 'res.company'

    tenant_id = fields.Selection(selection='_abk_xero_tenants', string="Tenant")
    is_login_xero = fields.Boolean('API Login?', store=False, compute='_compute_abk_xero_tenants')
    is_xero_config = fields.Boolean('Xero Config?', store=False, compute='_compute_abk_xero_config')

    _map_status = {
        # xero: odoo
        'DRAFT': 'not_paid',
        'SUBMITTED': 'reversed',
        'AUTHORISED': 'reversed',
        'PAID': 'paid',
        'DELETED': 'not_paid',
        'VOIDED': 'not_paid',
    }

    @api.depends()
    def _compute_abk_xero_config(self):
        xero = self.env['abk.xero.session']
        xero_config = xero.get_xero_config()
        for record in self:
            if xero_config.get('client_id', None):
                record['is_xero_config'] = True
            else:
                record['is_xero_config'] = False

    @api.depends()
    def _compute_abk_xero_tenants(self):
        xero = self.env['abk.xero.session']
        session = xero.get_xero_session()
        for record in self:
            if session.get('access_token', None):
                record['is_login_xero'] = True
            else:
                record['is_login_xero'] = False

    def _abk_xero_tenants(self):
        xero = self.env['abk.xero.session']
        session = xero.get_xero_session()
        lst = []
        if session.get('access_token', None):
            for tenant in session.get('tenants'):
                lst.append((tenant.get('tenantId'), tenant.get('tenantName')))
        return lst

    # BUTTONS EVENTS

    def abk_xero_config(self):
        xero = self.env['abk.xero.session']
        try:
            config = xero.search([('type', '=', 'Config')])[-1]
        except:
            config = None

        if not config:
            config = xero.create({
                'name': '{}',
                'type': 'Config'
            })

        return {
            'name': 'Xero Config',
            'domain': [],
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'abk.xero.session',
            'res_id': config.id,
            'target': 'new',
            'context': {
                'form_view_initial_mode': 'edit',
                'view_no_maturity': False
            },
        }

    def abk_xero_login(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/abk-xero-integration/get-token/',
            'target': 'new',
        }

    def abk_xero_import_invoices(self):
        self.import_invoices(self.tenant_id)

    def abk_xero_import_contacts(self):
        self.import_contacts(self.tenant_id)

    def abk_xero_import_products(self):
        self.import_products(self.tenant_id)

    def abk_xero_push_purchase_orders(self):
        self.push_purchase_orders(self.tenant_id)

    def abk_xero_push_invoices(self):
        self.push_invoices(self.tenant_id)

    # FUNCTIONS

    def get_company_from_tenant(self, xero_tenant_id):
        try:
            return self.search([('tenant_id', '=', xero_tenant_id)], limit=1)
        except:
            return None

    def import_accounts(self, xero_tenant_id):
        api_instance = AccountingApi(self.env['abk.xero.session'].get_api_client())
        api_response = api_instance.get_accounts(xero_tenant_id=xero_tenant_id)

    def import_contacts(self, xero_tenant_id):
        accounting_api = AccountingApi(self.env['abk.xero.session'].get_api_client())
        try:
            read_contacts = accounting_api.get_contacts(xero_tenant_id)
        except AccessTokenExpiredError as e:
            self.env['abk.xero.session'].refresh_token()
            read_contacts = accounting_api.get_contacts(xero_tenant_id)

        for read_contact in read_contacts.contacts:
            self.save_contact(read_contact)

    def save_contact(self, xero_contact):
        odoo_contact = self.env['res.partner']
        find_contact = odoo_contact.find_xero(xero_contact.contact_id)
        if find_contact:
            return find_contact.id

        contact_data = {
            'name': xero_contact.name,
            'xero_contact_id': xero_contact.contact_id,
            'xero_contact_number': xero_contact.contact_number,
            'email': xero_contact.email_address,
        }
        contact = odoo_contact.create(contact_data)
        self.env.cr.commit()
        return contact.id

    def import_products(self, xero_tenant_id):
        accounting_api = AccountingApi(self.env['abk.xero.session'].get_api_client())
        try:
            res = accounting_api.get_items(xero_tenant_id)
        except AccessTokenExpiredError as e:
            self.env['abk.xero.session'].refresh_token()
            res = accounting_api.get_items(xero_tenant_id)

        for item in res.items:
            self.save_product(item)

    def save_product(self, xero_product):
        product_data = {
            'name': xero_product.code,
            'display_name': xero_product.name,
            'default_code': xero_product.code,
            'list_price': xero_product.sales_details.unit_price,
            'description': xero_product.description,
            'xero_item_id': xero_product.item_id
        }

        odoo_product = self.env['product.template']
        product = odoo_product.search([('default_code', '=', xero_product.code)], limit=1)
        if product:
            product.write(product_data)
            self.env.cr.commit()
            return product

        product = odoo_product.create(product_data)
        self.env.cr.commit()
        return product

    def import_sale_orders(self, xero_tenant_id):
        sale_order = self.env['sale.order']

    def import_invoices(self, xero_tenant_id):
        api_instance = AccountingApi(self.env['abk.xero.session'].get_api_client())
        try:
            api_response = api_instance.get_invoices(xero_tenant_id=xero_tenant_id, statuses=['Paid'])
        except AccessTokenExpiredError as e:
            self.env['abk.xero.session'].refresh_token()
            api_response = api_instance.get_invoices(xero_tenant_id=xero_tenant_id, statuses=['Paid'])

        invoices = api_response.invoices
        for invoice in invoices:
            self.save_invoice(invoice)

    def save_invoice(self, xero_invoice):
        odoo_invoice = self.env['account.move']

        # check exist invoice
        o_inv = odoo_invoice.search([('name', '=', xero_invoice.invoice_number)], limit=1)
        if o_inv:
            return False

        # create new invoice
        contact_id = self.save_contact(xero_invoice.contact)
        invoice_data = {
            'name': xero_invoice.invoice_number,
            'partner_id': contact_id,
            'move_type': 'out_invoice',
            'invoice_date': xero_invoice.date,
            'invoice_date_due': xero_invoice.due_date,
        }

        invoice = odoo_invoice.search([('name', '=', xero_invoice.invoice_number)], limit=1)
        if invoice:
            invoice.write(invoice_data)
            return invoice

        is_valid = True
        invoice_line_ids = []
        for item in xero_invoice.line_items:
            product = self.env['product.template'].search([('default_code', '=', item.item_code)], limit=1)
            if not product:
                is_valid = False
                break

            invoice_line_ids.append((0, 0, {
                'quantity': item.quantity,
                'discount': item.discount_amount,
                'product_id': product.id,
                'name': item.item_code,
                'price_unit': item.line_amount,
            }))

        if is_valid:
            invoice_data['invoice_line_ids'] = invoice_line_ids
            invoice = odoo_invoice.create(invoice_data)
            self.env.cr.commit()
            return invoice

        return None

    def update_invoice_status(self, xero_invoice):
        _logger.info('--------------- updating invoice status: ' + str(xero_invoice.invoice_id))
        try:
            o_inv = self.env['account.move'].search([('xero_invoice_id', '=', xero_invoice.invoice_id)], limit=1)
            if not o_inv or o_inv.payment_state == 'paid':
                return None

            vals = {'payment_state': self._map_status.get(xero_invoice.status)}
            if xero_invoice.status == 'DELETED' or xero_invoice.status == 'VOIDED':
                vals['state'] = 'draft'

            _logger.info('--------------- updated status: ' + str(xero_invoice.invoice_id) + ': ' + str(o_inv.name))
            o_inv.write(vals)

            if xero_invoice.status == 'PAID':
                if o_inv.name:
                    self.make_payment_invoice(o_inv)
            return o_inv
        except Exception as e:
            _logger.info(e)
            return None

    def make_payment_invoice(self, invoice):
        _logger.info('make_payment: ' + str(invoice.name))
        payment_obj = self.env['account.payment'].with_context(default_invoice_ids=[(4, invoice.id, False)])
        payment = payment_obj.create({
            'date': fields.Date.today(),
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': invoice.partner_id.id,
            'amount': abs(invoice.amount_total),
            'currency_id': invoice.currency_id.id,
            'journal_id': 8,  # TODO
            'company_id': invoice.company_id.id,
            'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id
        })
        payment.action_post()
        _logger.info(payment)
        return True

    def get_xero_invoice(self, xero_tenant_id, xero_invoice_id):
        api_instance = AccountingApi(self.env['abk.xero.session'].get_api_client())
        try:
            res = api_instance.get_invoice(xero_tenant_id, xero_invoice_id)
        except AccessTokenExpiredError as e:
            self.env['abk.xero.session'].refresh_token()
            res = api_instance.get_invoice(xero_tenant_id, xero_invoice_id)
        except Exception as e:
            _logger.info(e)
            return None

        invoices = res.invoices
        return invoices[0]

    def push_contact(self, xero_tenant_id, odoo_contact, is_employee=False):
        if odoo_contact.xero_contact_id:
            return odoo_contact.xero_contact_id

        api_instance = AccountingApi(self.env['abk.xero.session'].get_api_client())
        xero_tenant_id = xero_tenant_id
        summarize_errors = True

        contact_name = odoo_contact.name

        if is_employee:
            contact_phone = odoo_contact.mobile_phone
        else:
            contact_phone = odoo_contact.phone

        if is_employee:
            contact_mobile = odoo_contact.work_phone
        else:
            contact_mobile = odoo_contact.mobile

        if is_employee:
            contact_email = odoo_contact.work_email
        else:
            contact_email = odoo_contact.email

        phones = []
        if contact_phone:
            phones.append(Phone(
                phone_number=contact_phone,
                phone_type="DEFAULT"))

        if contact_mobile:
            phones.append(Phone(
                phone_number=contact_mobile,
                phone_type="MOBILE"))

        contact = Contact(
            name=contact_name,
            email_address=contact_email,
            phones=phones)

        try:
            res = api_instance.update_or_create_contacts(xero_tenant_id, Contacts(contacts=[contact]),
                                                         summarize_errors)
        except AccessTokenExpiredError as e:
            self.env['abk.xero.session'].refresh_token()
            res = api_instance.update_or_create_contacts(xero_tenant_id, Contacts(contacts=[contact]),
                                                         summarize_errors)
        except:
            return None

        odoo_contact.write({'xero_contact_id': res.contacts[0].contact_id})
        return res.contacts[0].contact_id

    def push_purchase_orders(self, xero_tenant_id):
        _logger.info('----------------> push_purchase_orders')
        pushed_po = {}
        purchase_orders = []

        api_instance = AccountingApi(self.env['abk.xero.session'].get_api_client())
        summarize_errors = True

        company = self.get_company_from_tenant(xero_tenant_id)
        if not company:
            _logger.info('----------------> error_company')
            return False

        pos = self.env['purchase.order'].search([('state', '!=', 'draft'), ('company_id', '=', company.id)])
        for po in pos:
            if po.xero_po_id:
                continue

            date_value = po.date_order
            contact_id = self.push_contact(xero_tenant_id, po.partner_id)
            contact = Contact(contact_id=contact_id)
            line_items = []
            for order_line in po.order_line:
                item_code = None
                if order_line.product_id.xero_item_id:
                    item_code = order_line.product_id.default_code or order_line.product_id.name

                line_items.append(LineItem(
                    description=order_line.product_id.name,
                    item_code=item_code,
                    quantity=order_line.product_qty,
                    unit_amount=order_line.price_unit,
                    account_code="000"))

            purchase_orders.append(PurchaseOrder(
                purchase_order_number=po.name,
                contact=contact,
                line_items=line_items,
                date=date_value)
            )

            pushed_po[po.name] = po
            _logger.info('----------------> pushed: ' + str(po.name))

        res = None
        try:
            res = api_instance.update_or_create_purchase_orders(xero_tenant_id,
                                                                PurchaseOrders(purchase_orders=purchase_orders),
                                                                summarize_errors)
        except AccessTokenExpiredError as e:
            self.env['abk.xero.session'].refresh_token()
            res = api_instance.update_or_create_purchase_orders(xero_tenant_id,
                                                                PurchaseOrders(purchase_orders=purchase_orders),
                                                                summarize_errors)
        except AccountingBadRequestException as e:
            _logger.info("Exception when calling AccountingApi->createPurchaseOrders: %s\n" % e)

        if res:
            for xero_po in res.purchase_orders:
                number = xero_po.purchase_order_number
                _logger.info('----------------> success: ' + str(number))
                pushed_po.get(number).write({'xero_po_id': xero_po.purchase_order_id})

        return True

    def get_xero_invoice_data(self, xero_tenant_id, odoo_invoice):
        # xero_invoice_type is ACCPAY(bill) | ACCREC(sale invoice)
        if odoo_invoice.xero_invoice_id:
            return None

        if not odoo_invoice.partner_id:
            return None

        date_value = odoo_invoice.invoice_date
        due_date_value = odoo_invoice.invoice_date_due

        contact_id = self.push_contact(xero_tenant_id, odoo_invoice.partner_id)
        contact = Contact(contact_id=contact_id)

        line_item_tracking = LineItemTracking(
            tracking_category_id="00000000-0000-0000-0000-000000000000",
            tracking_option_id="00000000-0000-0000-0000-000000000000")

        line_items = []
        for invoice_line in odoo_invoice.invoice_line_ids:
            product = invoice_line.product_id
            item_code = product.xero_item_id or None
            line_items.append(LineItem(
                item_code=item_code,
                description=invoice_line.display_name,
                quantity=invoice_line.quantity,
                unit_amount=invoice_line.price_unit,
                account_code="000",
                tracking=[line_item_tracking]))

        xero_invoice_type = odoo_invoice.move_type == 'in_invoice' and 'ACCPAY' or 'ACCREC'

        return Invoice(
            type=xero_invoice_type,
            invoice_number=odoo_invoice.name,
            contact=contact,
            date=date_value or None,
            due_date=due_date_value or None,
            line_items=line_items,
            reference="Odoo",
            status="DRAFT")

    def push_invoice(self, xero_tenant_id, odoo_invoice):
        api_instance = AccountingApi(self.env['abk.xero.session'].get_api_client())
        summarize_errors = True
        xero_invoice_data = self.get_xero_invoice_data(xero_tenant_id, odoo_invoice)
        if xero_invoice_data:
            invoices = [xero_invoice_data]

            try:
                res = api_instance.update_or_create_invoices(xero_tenant_id, Invoices(invoices=invoices),
                                                             summarize_errors)
            except AccessTokenExpiredError as e:
                self.env['abk.xero.session'].refresh_token()
                res = api_instance.update_or_create_invoices(xero_tenant_id, Invoices(invoices=invoices),
                                                             summarize_errors)
            except AccountingBadRequestException as e:
                print("Exception when calling AccountingApi->createInvoices: %s\n" % e)
                return False

            xero_inv = res.invoices[0]
            odoo_invoice.write({'xero_invoice_id': xero_inv.invoice_number})

    def push_invoices(self, xero_tenant_id, odoo_state=None):
        # odoo_state invoice | bill | None
        _logger.info('----------------> push_invoices')
        pushed = {}
        invoices = []

        api_instance = AccountingApi(self.env['abk.xero.session'].get_api_client())
        xero_tenant_id = xero_tenant_id
        summarize_errors = True

        company = self.get_company_from_tenant(xero_tenant_id)
        if not company:
            _logger.info('----------------> error_company')
            return False

        if odoo_state == 'bill':
            odoo_invoices = self.env['account.move'].search(
                [('xero_invoice_id', '=', None), ('state', '=', 'posted'), ('move_type', '=', 'in_invoice'),
                 ('company_id', '=', company.id)])
        elif odoo_state == 'invoice':
            odoo_invoices = self.env['account.move'].search(
                [('xero_invoice_id', '=', None), ('state', '=', 'posted'), ('move_type', '=', 'out_invoice'),
                 ('company_id', '=', company.id)])
        else:
            odoo_invoices = self.env['account.move'].search(
                [('xero_invoice_id', '=', None), ('state', '=', 'posted'), ('company_id', '=', company.id)])

        for odoo_invoice in odoo_invoices:
            xero_invoice_data = self.get_xero_invoice_data(xero_tenant_id, odoo_invoice)
            if xero_invoice_data:
                invoices.append(xero_invoice_data)
                pushed[odoo_invoice.name] = odoo_invoice
                _logger.info('----------------> pushed: ' + str(odoo_invoice.name))

        res = None
        try:
            res = api_instance.update_or_create_invoices(xero_tenant_id, Invoices(invoices=invoices), summarize_errors)
        except AccessTokenExpiredError as e:
            self.env['abk.xero.session'].refresh_token()
            res = api_instance.update_or_create_invoices(xero_tenant_id, Invoices(invoices=invoices), summarize_errors)
        except AccountingBadRequestException as e:
            print("Exception when calling AccountingApi->createInvoices: %s\n" % e)

        if res:
            for xero_inv in res.invoices:
                number = xero_inv.invoice_number
                _logger.info('----------------> success: ' + str(number))
                pushed.get(number).write({'xero_invoice_id': xero_inv.invoice_id})

        return True

    def get_xero_bill_from_expense_sheet(self, xero_tenant_id, expense_sheet):
        if expense_sheet.xero_invoice_id:
            return None

        if not expense_sheet.employee_id:
            return None

        try:
            contact_id = self.push_contact(xero_tenant_id, expense_sheet.employee_id, is_employee=True)
        except:
            _logger.info('----------> ERROR CREATE CONTACT')
            return None

        contact = Contact(contact_id=contact_id)

        line_items = []
        for it in expense_sheet.expense_line_ids:
            item_code = None
            team_name = it.employee_id.department_id and it.employee_id.department_id.name or ''
            description = str(team_name) + ' ' + str(it.project_code) + ' ' + str(it.display_name)
            description = description.strip()

            tracking = []
            project_code_tracking = self.fixed_xero_tracking(xero_tenant_id, 'hr.expense.project_code', it.project_code)
            tracking.append(LineItemTracking(
                tracking_category_id=project_code_tracking.get('category_id'),
                tracking_option_id=project_code_tracking.get('option_id')))

            team_tracking = self.fixed_xero_tracking(xero_tenant_id, 'hr.expense.team_name', team_name)
            tracking.append(LineItemTracking(
                tracking_category_id=team_tracking.get('category_id'),
                tracking_option_id=team_tracking.get('option_id')))

            line_items.append(LineItem(
                item_code=item_code,
                description=description,
                quantity=it.quantity,
                unit_amount=it.unit_amount,
                account_code="000",
                tracking=tracking))

        xero_invoice_type = 'ACCPAY'
        invoice_number = self.get_xero_ref_from_expense(expense_sheet)

        return Invoice(
            type=xero_invoice_type,
            invoice_number=invoice_number,
            contact=contact,
            date=None,
            due_date=None,
            line_items=line_items,
            reference="Odoo",
            status="DRAFT")

    def fixed_xero_tracking(self, xero_tenant_id, ofield, ovalue):
        otracking = self.env['abk.xero.tracking.category'].get_xero_mapping(ofield, ovalue)
        if not otracking.get('category_id'):
            return {
                "category_id": '00000000-0000-0000-0000-000000000000',
                "option_id": '00000000-0000-0000-0000-000000000000',
            }

        if otracking.get('option_id'):
            return {
                "category_id": otracking.get('category_id'),
                "option_id": otracking.get('option_id'),
            }

        api_instance = AccountingApi(self.env['abk.xero.session'].get_api_client())
        xero_tenant_id = xero_tenant_id
        xero_category_id = otracking.get('category_id')
        xero_option_id = None

        need_create_option = False
        res = None

        try:
            res = api_instance.get_tracking_category(xero_tenant_id, xero_category_id)
        except AccessTokenExpiredError as e:
            self.env['abk.xero.session'].refresh_token()
            res = api_instance.get_tracking_category(xero_tenant_id, xero_category_id)
        except Exception as e:
            _logger.error(e)

        if res:
            options = res.tracking_categories and res.tracking_categories[0] and res.tracking_categories[
                0].options or []
            for opt in options:
                if opt.name == ovalue:
                    xero_option_id = opt.tracking_option_id
                    need_create_option = True
                    break

        if not xero_option_id:
            _logger.info('Create Option: ' + str(ovalue))
            # create option
            tracking_option = TrackingOption(name=ovalue)
            try:
                res2 = api_instance.create_tracking_options(xero_tenant_id, xero_category_id, tracking_option)
                xero_option_id = res2.options and res2.options[0] and res2.options[0].tracking_option_id or None
                need_create_option = True
            except AccessTokenExpiredError as e:
                self.env['abk.xero.session'].refresh_token()
                res2 = api_instance.create_tracking_options(xero_tenant_id, xero_category_id, tracking_option)
                xero_option_id = res2.options and res2.options[0] and res2.options[0].tracking_option_id or None
                need_create_option = True
            except Exception as e:
                _logger.error(e)

        if need_create_option and xero_option_id:
            # create in odoo
            self.env['abk.xero.tracking.category.option'].create({
                "category_id": otracking.get('o_category_id'),
                "ovalue": ovalue,
                "xero_category_option_id": xero_option_id
            })

        return {
            "category_id": xero_category_id,
            "option_id": xero_option_id or '00000000-0000-0000-0000-000000000000',
        }

    def get_xero_ref_prefix_from_expense(self, expense_sheet):
        for line in expense_sheet.expense_line_ids:
            if not line.reference:
                return 'Odoo'
        return 'EXP'

    def get_xero_ref_from_expense(self, expense_sheet):
        prefix = self.get_xero_ref_prefix_from_expense(expense_sheet)
        str_format = str(prefix) + "{0:09d}"
        return str_format.format(int(expense_sheet.id))

    def update_expense_sheet_status_from_xero(self, xero_invoice):
        _logger.info('--------------- updating expense status: ' + str(xero_invoice.invoice_id))
        try:
            if xero_invoice.status != 'PAID' or xero_invoice.status != 'VOIDED':
                return None

            expense_sheet = self.env['hr.expense.sheet'].search([('xero_invoice_id', '=', xero_invoice.invoice_id)],
                                                                limit=1)
            if not expense_sheet or expense_sheet.state == 'approve':
                return None

            _logger.info('--------------- updated expense status: ' + str(xero_invoice.invoice_id) + ': ' + str(expense_sheet.name))

            if xero_invoice.status == 'PAID':
                expense_sheet.write({'state': 'approve'})
            if xero_invoice.status == 'VOIDED':
                expense_sheet.write({'state': 'draft'})

        except Exception as e:
            _logger.info(e)
            return None

    def push_hr_expense_sheet(self, xero_tenant_id, expense_sheet):
        api_instance = AccountingApi(self.env['abk.xero.session'].get_api_client())
        summarize_errors = True
        xero_invoice_data = self.get_xero_bill_from_expense_sheet(xero_tenant_id, expense_sheet)
        if xero_invoice_data:
            invoices = [xero_invoice_data]

            try:
                res = api_instance.update_or_create_invoices(xero_tenant_id, Invoices(invoices=invoices),
                                                             summarize_errors)
            except AccessTokenExpiredError as e:
                self.env['abk.xero.session'].refresh_token()
                res = api_instance.update_or_create_invoices(xero_tenant_id, Invoices(invoices=invoices),
                                                             summarize_errors)
            except AccountingBadRequestException as e:
                _logger.info("Exception when calling AccountingApi->createInvoices: %s\n" % e)
                return False

            xero_inv = res.invoices[0]
            expense_sheet.write({'xero_invoice_id': xero_inv.invoice_number})

    def push_hr_expense_sheets(self, xero_tenant_id):
        pushed = {}
        invoices = []

        api_instance = AccountingApi(self.env['abk.xero.session'].get_api_client())
        xero_tenant_id = xero_tenant_id
        summarize_errors = True

        company = self.get_company_from_tenant(xero_tenant_id)
        if not company:
            _logger.info('----------------> ERROR_COMPANY')
            return False

        expense_sheets = self.env['hr.expense.sheet'].search(
            [('xero_invoice_id', '=', None), ('state', '=', 'approve'), ('company_id', '=', company.id)])

        is_call_api = False
        for expense_sheet in expense_sheets:
            xero_invoice_data = self.get_xero_bill_from_expense_sheet(xero_tenant_id, expense_sheet)
            if xero_invoice_data:
                invoices.append(xero_invoice_data)
                invoice_number = self.get_xero_ref_from_expense(expense_sheet)
                pushed[str(invoice_number)] = expense_sheet
                is_call_api = True

        if not is_call_api:
            _logger.info('----------> EMPTY DATA')
            return False

        res = None
        try:
            res = api_instance.update_or_create_invoices(xero_tenant_id, Invoices(invoices=invoices), summarize_errors)
        except AccessTokenExpiredError as e:
            self.env['abk.xero.session'].refresh_token()
            res = api_instance.update_or_create_invoices(xero_tenant_id, Invoices(invoices=invoices), summarize_errors)
        except AccountingBadRequestException as e:
            print("Exception when calling AccountingApi->createInvoices: %s\n" % e)
        except:
            _logger.info('----------> ERROR CALL API')

        if res:
            for xero_inv in res.invoices:
                number = xero_inv.invoice_number
                _logger.info('----------------> SUCCESS: ' + str(number))
                pushed.get(number).write({'xero_invoice_id': xero_inv.invoice_id})

        return True

    def process_webhooks_event(self, event):
        tenant_id = event.get('tenantId')
        resource_id = event.get('resourceId')
        if event.get('eventCategory') == 'INVOICE':
            xero_invoice = self.get_xero_invoice(tenant_id, resource_id)
            if xero_invoice:
                # update invoice status
                self.update_invoice_status(xero_invoice)
                # update expense
                self.update_expense_sheet_status_from_xero(xero_invoice)

    def cron_abk_xero_test(self, options):
        company_id = options.get('company_id', 1)
        xero_tenant_id = self.search([('id', '=', company_id)], limit=1).tenant_id
        result = self.fixed_xero_tracking(xero_tenant_id, options.get('ofield'), options.get('ovalue'))
        _logger.info(result)

    def cron_update_invoices(self, company_id):
        _logger.info('___________________ cron_update_invoices')
        try:
            xero_tenant_id = self.search([('id', '=', company_id)], limit=1).tenant_id

            odoo_invoices = self.env['account.move'].search(
                [('xero_invoice_id', '!=', None), ('state', '=', 'posted'), ('payment_state', '!=', 'paid')])
            invoice_numbers = []

            for odoo_invoice in odoo_invoices:
                if odoo_invoice.name:
                    invoice_numbers.append(odoo_invoice.name)

            if invoice_numbers:
                api_instance = AccountingApi(self.env['abk.xero.session'].get_api_client())
                try:
                    res = api_instance.get_invoices(xero_tenant_id, invoice_numbers=invoice_numbers)
                except AccessTokenExpiredError as e:
                    self.env['abk.xero.session'].refresh_token()
                    res = api_instance.get_invoices(xero_tenant_id, invoice_numbers=invoice_numbers)

                for invoice in res.invoices:
                    self.update_invoice_status(invoice)
        except:
            _logger.info('___________________ERROR')
            return None

    def cron_sync_purchase_orders(self, company_id):
        _logger.info('_____________ Cron Push Purchase Orders')
        try:
            xero_tenant_id = self.search([('id', '=', company_id)], limit=1).tenant_id
        except:
            _logger.info('___________________ERROR')
            return False

        if not xero_tenant_id:
            return False

        self.push_purchase_orders(xero_tenant_id)

    def cron_sync_invoices(self, company_id, state=None):
        _logger.info('_____________ Cron Push Invoices')
        try:
            xero_tenant_id = self.search([('id', '=', company_id)], limit=1).tenant_id
        except:
            _logger.info('___________________ERROR')
            return False

        if not xero_tenant_id:
            return False

        self.push_invoices(xero_tenant_id, odoo_state=state)

    def cron_push_hr_expense_sheets(self, company_id):
        _logger.info('_____________ CRON PUSH HR_EXPENSE_SHEET')
        try:
            xero_tenant_id = self.search([('id', '=', company_id)], limit=1).tenant_id
        except:
            _logger.info('___________________ERROR')
            return False

        if not xero_tenant_id:
            return False

        _logger.info('___________________ START CRON_PUSH_HR_EXPENSE_SHEETS')
        self.push_hr_expense_sheets(xero_tenant_id)
