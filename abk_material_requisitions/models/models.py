# -*- coding: utf-8 -*-

from datetime import datetime, time
from dateutil.relativedelta import relativedelta
from itertools import groupby
from pytz import timezone, UTC

from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_is_zero
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang, format_amount


class res_partner(models.Model):
    _inherit = 'res.partner'

    receipt_reminder_email = fields.Boolean('Receipt Reminder', default=False, company_dependent=True,
                                            help="Automatically send a confirmation email to the vendor X days before the expected receipt date, asking him to confirm the exact date.")
    reminder_date_before_receipt = fields.Integer('Days Before Receipt', default=1, company_dependent=True,
                                                  help="Number of days to send reminder email before the promised receipt date")


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    vendor_partner_id = fields.Many2one('res.partner', string='Vendor', store=True, required=True,
                                        config_parameter="abk_material_requisitions.vendor_partner_id")


class CustomPurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    terms_conditions = fields.Many2one('abk.terms.conditions', string='Terms & Conditions')
    term_description = fields.Text(related='terms_conditions.description', string='Term Description')

    @api.onchange('terms_conditions')
    def _onchange_terms_conditions(self):
        for record in self:
            record['notes'] = record.term_description


class MaterialRequisitions(models.Model):
    _name = 'abk.material.requisitions'
    _description = 'Material Requisitions'
    _order = 'priority desc, id desc'

    READONLY_STATES = {
        'approved': [('readonly', True)],
        'cancel': [('readonly', True)],
    }

    name = fields.Char('Auto PR Number', required=True, index=True, copy=False, default='New')
    priority = fields.Selection(
        [('0', 'Normal'), ('1', 'Urgent')], 'Priority', default='0', index=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('cancel', 'Cancelled')
    ], string='Status', readonly=True, index=True, copy=False, default='draft', tracking=True)

    description = fields.Text(string="Description")
    revision = fields.Integer(sring="Revision", required="True")
    date_order = fields.Datetime('PO Order Deadline', required=True, states=READONLY_STATES, index=True, copy=False,
                                 default=fields.Datetime.now)
    date_approve = fields.Datetime('Confirmation Date', readonly=1, index=True, copy=False)
    receipt_date = fields.Datetime(string="Receipt Date", required=False, index=True, copy=False,
                                   default=fields.Datetime.now)
    self_collection = fields.Boolean('Self Collection', default=False, readonly=False)

    order_id = fields.Many2one('sale.order', string='Sales Order', required=False, change_default=True, tracking=True)
    notes = fields.Text('Terms and Conditions')
    project_code = fields.Selection(selection='_auto_get_project_codes', string="Project Code", store=True,
                                    required=False)

    partner_id = fields.Many2one('res.partner', string='Customer', required=True, states=READONLY_STATES,
                                 change_default=True, tracking=True)
    contact_phone = fields.Char(related='partner_id.phone', string="Customer Phone Number")
    partner_invoice_id = fields.Many2one('res.partner', string='Invoice Address', readonly=True, required=False)
    partner_shipping_id = fields.Many2one('res.partner', string='Delivery Address', readonly=True, required=False)
    receipt_reminder_email = fields.Boolean('Receipt Reminder Email', related='partner_id.receipt_reminder_email',
                                            readonly=False)
    reminder_date_before_receipt = fields.Integer('Days Before Receipt',
                                                  related='partner_id.reminder_date_before_receipt', readonly=False)

    product_id = fields.Many2one('product.product', related='mr_line.product_id', string='Product', readonly=False)
    mr_line = fields.One2many('abk.material.requisitions.line', 'mr_id', string='MR Lines', copy=True,
                              states={'cancel': [('readonly', True)], 'approved': [('readonly', True)]})
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all',
                                     tracking=True)
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all')
    currency_id = fields.Many2one('res.currency', 'Currency', required=True, states=READONLY_STATES,
                                  default=lambda self: self.env.company.currency_id.id)
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, states=READONLY_STATES,
                                 default=lambda self: self.env.company.id)
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position',
                                         domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    user_id = fields.Many2one(
        'res.users', string='Representative', index=True, tracking=True,
        default=lambda self: self.env.user, check_company=True)
    origin = fields.Char('Source Document', copy=False,
                         help="Reference of the document that generated this purchase order "
                              "request (e.g. a sales order)")
    MP = fields.Char(String="MP")
    Q = fields.Char(String="Q")
    CM = fields.Char(String="CM")
    attn = fields.Char(String="Attn")

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('abk.material.requisitions')
        return super(MaterialRequisitions, self).create(vals)

    @api.depends('mr_line.price_total')
    def _amount_all(self):
        for mr in self:
            amount_untaxed = amount_tax = 0.0
            for line in mr.mr_line:
                line._compute_amount()
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            currency = mr.currency_id or mr.partner_id.property_purchase_currency_id or self.env.company.currency_id
            mr.update({
                'amount_untaxed': currency.round(amount_untaxed),
                'amount_tax': currency.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax,
            })

    @api.onchange('fiscal_position_id', 'company_id')
    def _compute_tax_id(self):
        """
        Trigger the recompute of the taxes if the fiscal position is changed on the PO.
        """
        self.mr_line._compute_tax_id()

    def _auto_get_project_codes(self):
        lst = []
        sale_orders = self.env['sale.order'].sudo().read_group(
            [('project_code', '!=', ''), ('project_code', '!=', None)],
            ['project_code'],
            ['project_code'])
        for sale_order in sale_orders:
            lst.append((sale_order.get('project_code'), sale_order.get('project_code')))
        return lst

    def button_submitted(self):
        for order in self:
            if order.state not in ['draft']:
                continue
            # Deal with double validation process
            order.write({'state': 'submitted'})
        return True

    def button_approved(self):
        vendor_partner_id = self.env['ir.config_parameter'].sudo().get_param(
            'abk_material_requisitions.vendor_partner_id')
        if not vendor_partner_id:
            notification = {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Invalid fields:',
                    'message': 'Product has not vendor.',
                    'type': 'danger',  # types: success,warning,danger,info
                    'sticky': False,  # True/False will display for few seconds if false
                },
            }
            return notification

        partner_ids = []
        default_partner_ids = []
        for line in self.mr_line:
            if not line.product_id.product_tmpl_id.seller_ids:
                default_partner_ids.append(int(vendor_partner_id))
            else:
                partner_ids.append(line.product_id.product_tmpl_id.seller_ids.name[0].id)

        # Product hasn't vendor
        a = {}
        for x in default_partner_ids:
            if not a.get(x):
                a[x] = []
            a[x].append(x)

        for p0 in a:
            purchase_order = self.env["purchase.order"].create(
                {
                    "name": 'Create from MR - ' + self.env['ir.sequence'].next_by_code('purchase.order'),
                    "partner_id": p0,
                    "notes": str(self.notes),
                }
            )
            purchase_order_id_0 = purchase_order.id
            for line in self.mr_line:
                if not line.product_id.product_tmpl_id.seller_ids:
                    self.env["purchase.order.line"].create(
                        {
                            "name": line.name,
                            "product_id": line.product_id.id,
                            "order_id": purchase_order_id_0,
                            "product_qty": line.product_qty,
                            "price_unit": line.price_unit,
                        }
                    )

        # Product has vendor
        r = {}
        for item in partner_ids:
            if not r.get(item):
                r[item] = []
            r[item].append(item)

        for po in r:
            purchase_order = self.env["purchase.order"].create(
                {
                    "name": 'Create from MR - ' + self.env['ir.sequence'].next_by_code('purchase.order'),
                    "partner_id": po,
                    "notes": str(self.notes),
                }
            )
            purchase_order_id = purchase_order.id
            for j in r[po]:
                for line in self.mr_line:
                    if not line.product_id.product_tmpl_id.seller_ids:
                        continue
                    elif line.product_id.product_tmpl_id.seller_ids.name[0].id == j:
                        self.env["purchase.order.line"].create(
                            {
                                "name": line.name,
                                "product_id": line.product_id.id,
                                "order_id": purchase_order_id,
                                "product_qty": line.product_qty,
                                "price_unit": line.price_unit,
                            }
                        )
                break

        for order in self:
            if order.state not in ['submitted']:
                continue
            # Deal with double validation process
            order.write({'state': 'approved', 'date_approve': fields.Datetime.now()})
        return True

    def button_cancel(self):
        self.write({'state': 'cancel'})

    def button_draft(self):
        self.write({'state': 'draft'})
        return {}

    def unlink(self):
        for order in self:
            if not order.state == 'cancel':
                raise UserError(_('In order to delete a material requisition, you must cancel it first.'))
        return super(MaterialRequisitions, self).unlink()


class MaterialRequisitionsLine(models.Model):
    _name = 'abk.material.requisitions.line'
    _description = 'Material Requisitions Line'
    _order = 'mr_id, sequence, id'

    name = fields.Text(string='Description', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    product_qty = fields.Float(string='Quantity', digits='Product Unit of Measure', required=True)
    product_uom_qty = fields.Float(string='Total Quantity', compute='_compute_product_uom_qty', store=True)
    date_planned = fields.Datetime(string='Delivery Date', index=True,
                                   help="Delivery date expected from vendor. This date respectively defaults to vendor pricelist lead time then today's date.")
    taxes_id = fields.Many2many('account.tax', string='Taxes',
                                domain=['|', ('active', '=', False), ('active', '=', True)])
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure',
                                  domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    product_id = fields.Many2one('product.product', string='Product', domain=[('purchase_ok', '=', True)],
                                 change_default=True)
    product_type = fields.Selection(related='product_id.type', readonly=True)
    price_unit = fields.Float(string='Unit Price', required=True, digits='Product Price')

    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', store=True)
    price_tax = fields.Float(compute='_compute_amount', string='Tax', store=True)

    mr_id = fields.Many2one('abk.material.requisitions', string='MR Reference', index=True, required=True,
                            ondelete='cascade')
    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_note', "Note")], default=False, help="Technical field for UX purpose.")
    currency_id = fields.Many2one(related='mr_id.currency_id', store=True, string='Currency', readonly=True)
    company_id = fields.Many2one('res.company', related='mr_id.company_id', string='Company', store=True,
                                 readonly=True)
    state = fields.Selection(related='mr_id.state', store=True)
    partner_id = fields.Many2one('res.partner', related='mr_id.partner_id', string='Partner', readonly=True,
                                 store=True)
    date_order = fields.Datetime(related='mr_id.date_order', string='Order Date', readonly=True)

    @api.depends('product_qty', 'price_unit', 'taxes_id')
    def _compute_amount(self):
        for line in self:
            vals = line._prepare_compute_all_values()
            taxes = line.taxes_id.compute_all(
                vals['price_unit'],
                vals['currency_id'],
                vals['product_qty'],
                vals['product'],
                vals['partner'])
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })

    def _prepare_compute_all_values(self):
        # Hook method to returns the different argument values for the
        # compute_all method, due to the fact that discounts mechanism
        # is not implemented yet on the purchase orders.
        # This method should disappear as soon as this feature is
        # also introduced like in the sales module.
        self.ensure_one()
        return {
            'price_unit': self.price_unit,
            'currency_id': self.mr_id.currency_id,
            'product_qty': self.product_qty,
            'product': self.product_id,
            'partner': self.mr_id.partner_id,
        }

    @api.depends('product_uom', 'product_qty', 'product_id.uom_id')
    def _compute_product_uom_qty(self):
        for line in self:
            if line.product_id and line.product_id.uom_id != line.product_uom:
                line.product_uom_qty = line.product_uom._compute_quantity(line.product_qty, line.product_id.uom_id)
            else:
                line.product_uom_qty = line.product_qty

    @api.onchange('product_id')
    def onchange_product_id(self):
        if not self.product_id:
            return

        # Reset date, price and quantity since _onchange_quantity will provide default values
        self.price_unit = self.product_qty = 0.0

        self._product_id_change()

        self._suggest_quantity()
        self._onchange_quantity()

    def _product_id_change(self):
        if not self.product_id:
            return

        self.product_uom = self.product_id.uom_po_id or self.product_id.uom_id
        product_lang = self.product_id.with_context(
            lang=get_lang(self.env, self.partner_id.lang).code,
            partner_id=self.partner_id.id,
            company_id=self.company_id.id,
        )
        self.name = self._get_product_purchase_description(product_lang)

        self._compute_tax_id()

    def _compute_tax_id(self):
        for line in self:
            line = line.with_company(line.company_id)
            fpos = line.mr_id.fiscal_position_id or line.mr_id.fiscal_position_id.get_fiscal_position(
                line.mr_id.partner_id.id)
            # filter taxes by company
            taxes = line.product_id.supplier_taxes_id.filtered(lambda r: r.company_id == line.env.company)
            line.taxes_id = fpos.map_tax(taxes, line.product_id, line.mr_id.partner_id)

    def _suggest_quantity(self):
        '''
        Suggest a minimal quantity based on the seller
        '''
        if not self.product_id:
            return
        seller_min_qty = self.product_id.seller_ids \
            .filtered(
            lambda r: r.name == self.mr_id.partner_id and (not r.product_id or r.product_id == self.product_id)) \
            .sorted(key=lambda r: r.min_qty)
        if seller_min_qty:
            self.product_qty = seller_min_qty[0].min_qty or 1.0
            self.product_uom = seller_min_qty[0].product_uom
        else:
            self.product_qty = 1.0

    @api.onchange('product_qty', 'product_uom')
    def _onchange_quantity(self):
        if not self.product_id:
            return
        params = {'mr_id': self.mr_id}
        seller = self.product_id._select_seller(
            partner_id=self.partner_id,
            quantity=self.product_qty,
            date=self.mr_id.date_order and self.mr_id.date_order.date(),
            uom_id=self.product_uom,
            params=params)

        if seller or not self.date_planned:
            self.date_planned = self._get_date_planned(seller).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        # If not seller, use the standard price. It needs a proper currency conversion.
        if not seller:
            po_line_uom = self.product_uom or self.product_id.uom_po_id
            price_unit = self.env['account.tax']._fix_tax_included_price_company(
                self.product_id.uom_id._compute_price(self.product_id.standard_price, po_line_uom),
                self.product_id.supplier_taxes_id,
                self.taxes_id,
                self.company_id,
            )
            if price_unit and self.mr_id.currency_id and self.mr_id.company_id.currency_id != self.mr_id.currency_id:
                price_unit = self.mr_id.company_id.currency_id._convert(
                    price_unit,
                    self.mr_id.currency_id,
                    self.mr_id.company_id,
                    self.date_order or fields.Date.today(),
                )

            self.price_unit = price_unit
            return

        price_unit = self.env['account.tax']._fix_tax_included_price_company(seller.price,
                                                                             self.product_id.supplier_taxes_id,
                                                                             self.taxes_id,
                                                                             self.company_id) if seller else 0.0
        if price_unit and seller and self.mr_id.currency_id and seller.currency_id != self.mr_id.currency_id:
            price_unit = seller.currency_id._convert(
                price_unit, self.mr_id.currency_id, self.mr_id.company_id, self.date_order or fields.Date.today())

        if seller and self.product_uom and seller.product_uom != self.product_uom:
            price_unit = seller.product_uom._compute_price(price_unit, self.product_uom)

        self.price_unit = price_unit
        product_ctx = {'seller_id': seller.id, 'lang': get_lang(self.env, self.partner_id.lang).code}
        self.name = self._get_product_purchase_description(self.product_id.with_context(product_ctx))

    @api.model
    def _get_date_planned(self, seller, po=False):
        """Return the datetime value to use as Schedule Date (``date_planned``) for
           PO Lines that correspond to the given product.seller_ids,
           when ordered at `date_order_str`.

           :param Model seller: used to fetch the delivery delay (if no seller
                                is provided, the delay is 0)
           :param Model po: purchase.order, necessary only if the PO line is
                            not yet attached to a PO.
           :rtype: datetime
           :return: desired Schedule Date for the PO line
        """
        date_order = po.date_order if po else self.mr_id.date_order
        if date_order:
            date_planned = date_order + relativedelta(days=seller.delay if seller else 0)
        else:
            date_planned = datetime.today() + relativedelta(days=seller.delay if seller else 0)
        return self._convert_to_middle_of_day(date_planned)

    def _convert_to_middle_of_day(self, date):
        """Return a datetime which is the noon of the input date(time) according
        to order user's time zone, convert to UTC time.
        """
        tz = timezone(self.mr_id.user_id.tz or self.company_id.partner_id.tz or 'UTC')
        date = date.astimezone(tz)  # date is UTC, applying the offset could change the day
        return tz.localize(datetime.combine(date, time(12))).astimezone(UTC).replace(tzinfo=None)

    def _get_product_purchase_description(self, product_lang):
        self.ensure_one()
        name = product_lang.display_name
        if product_lang.description_purchase:
            name += '\n' + product_lang.description_purchase

        return name

    def unlink(self):
        for line in self:
            if line.order_id.state in ['approved']:
                raise UserError(
                    _('Cannot delete a material requisitions line which is in state \'%s\'.') % (line.state,))
        return super(MaterialRequisitionsLine, self).unlink()
