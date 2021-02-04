# -*- coding: utf-8 -*-

from odoo import models, fields, api
import datetime


class OrderCustomerImport(models.TransientModel):
    _name = 'amgl.order_customer_import'
    _description = 'Order And Customer Data Import'

    @api.multi
    def write(self, vals):
        product_code = vals.get('product_code', False)
        transaction_number = vals.get('transaction_number', False)
        quantity = vals.get('quantity', False)
        account_number = vals.get('account_number', False)
        first_name = vals.get('first_name', False)
        last_name = vals.get('last_name', False)
        account_type = vals.get('account_type', False)
        product_id = self._get_product_id(product_code)
        customer_id = self._get_customer_id(account_number)
        if customer_id:
            order_line = {
                'products': product_id,
                'customer_id': customer_id,
                'transaction_number': transaction_number,
                'quantity': quantity
            }
            self.env['amgl.order_line'].create(order_line)
        else:
            new_customer = {
                'gst_account_number': account_number,
                'account_number': account_number,
                'first_name': first_name,
                'last_name': last_name,
                'create_date': datetime.datetime.now(),
                'date_opened': datetime.datetime.now(),
                'account_type': account_type,
                'custodian_id': 1
            }
            self.env['amgl.customer'].create(new_customer)
        return super(OrderCustomerImport, self).create(vals)

    @api.model
    def create(self, vals):
        import_instances = self.env["amgl.order_customer_import"].search([]).unlink()
        product_code = vals.get('product_code', False)
        transaction_number = vals.get('transaction_number', False)
        quantity = vals.get('quantity', False)
        account_number = vals.get('account_number', False)
        first_name = vals.get('first_name', False)
        last_name = vals.get('last_name', False)
        account_type = vals.get('account_type', False)
        product_id = self._get_product_id(product_code)
        customer_id = self._get_customer_id(account_number)
        if customer_id:
            order_line = {
                'products': product_id,
                'customer_id': customer_id,
                'transaction_number': transaction_number,
                'quantity': quantity
            }
            self.env['amgl.order_line'].create(order_line)
        else:
            new_customer = {
                'gst_account_number': account_number,
                'account_number': account_number,
                'first_name': first_name,
                'last_name': last_name,
                'create_date': datetime.datetime.now(),
                'date_opened': datetime.datetime.now(),
                'account_type': account_type,
                'custodian_id': 1
            }
            self.env['amgl.customer'].create(new_customer)
        return super(OrderCustomerImport, self).create(vals)

    def _get_product_id(self, product_code):
        if product_code:
            product = self.env['amgl.products'].search([
                ('product_code', '=', product_code)
            ])
            if len(product) == 1:
                return product.id
            elif len(product) == 0:
                raise Warning('Product code not found: %s' % product_code)
            else:
                raise Warning('More than one product_code found: %s'% product_code)
        else:
            return False

    def _get_customer_id(self, account_number):
        if account_number:
            customer = self.env['amgl.customer'].search(['|',
                ('gst_account_number', '=', account_number),
                ('account_number', '=', account_number)
            ])
            if len(customer) == 1:
                return customer.id
            elif len(customer) == 0:
                raise Warning('Customer not found: %s' % account_number)
            else:
                raise Warning('More than one customer found: %s' % account_number)
        else:
            return False

    name = fields.Char(default='Delete Me Before Import')
    gst_account_number = fields.Char(string='GoldStar Account Number')
    product_code = fields.Char(string='Product Code')
    transaction_number = fields.Char(string='Transaction Number')
    quantity = fields.Char(string='Quantity')
    account_number = fields.Char(string='Account Number')
    first_name = fields.Char(string='First Name')
    last_name = fields.Char(string='Last Name')
    account_type = fields.Selection(selection=[('Commingled', 'Commingled'),
                                               ('Segregated', 'Segregated')])
    customer_id = fields.Char(string='Customer Name')
