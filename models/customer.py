# -*- coding: utf-8 -*-

import json
import math
import uuid
import urllib
import ftplib
import base64
import calendar
import datetime
import platform
import xlsxwriter
import pytz
from lxml import etree
from datetime import date
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class Customer(models.Model):
    _name = 'amgl.customer'
    _rec_name = 'full_name'
    _description = 'IRA Customer'
    _order = 'last_name,first_name,account_number asc'
    _sql_constraints = [
        ('uniq_account_number', 'unique(account_number)', 'Account number already exists!'),
        ('uniq_gst_account_number', 'unique(gst_account_number)', 'GoldStar Account number already exists!')
    ]

    gold_price = 0
    silver_price = 0
    platinum_price = 0
    palladium_price = 0

    @api.multi
    def _compile_fullname(self):
        for customer in self:
            first_name = ''
            if customer.first_name is False:
                first_name = customer.name
            else:
                first_name = customer.first_name
            fullname = first_name + ' ' + customer.last_name
            customer.update({
                'full_name': fullname,
                'first_name': first_name
            })

    @api.multi
    def _get_number_of_orders(self):
        number_of_records = 0
        for customer in self:
            for order in customer.customer_order_lines:
                number_of_records += 1
            customer.update({
                'number_of_orders': number_of_records
            })

    @api.one
    @api.depends('customer_order_lines2.products', 'customer_order_lines2.total_received_quantity')
    def _calculate_existing_inventory(self):
        gold_price, palladium_price, platinum_price, silver_price = self.get_spot_price_from_amark()
        for customer in self:
            total_gold = total_silver = total_platinum = total_palladium = total = 0
            total_weight = gold_weight = silver_weight = platinum_weight = palladium_weight = 0
            for line in self.customer_order_lines2:
                for p in line.products:
                    qty = float(line.total_received_quantity)
                    if p['type'] == 'Gold':
                        total_gold += qty
                        total += qty
                        gold_weight += self.calculate_weights(p, qty)
                        total_weight += self.calculate_weights(p, qty)
                    if p['type'] == 'Silver':
                        total_silver += qty
                        total += qty
                        silver_weight += self.calculate_weights(p, qty)
                        total_weight += self.calculate_weights(p, qty)
                    if p['type'] == 'Platinum':
                        total_platinum += qty
                        total += qty
                        platinum_weight += self.calculate_weights(p, qty)
                        total_weight += self.calculate_weights(p, qty)
                    if p['type'] == 'Palladium':
                        total_palladium += qty
                        total += qty
                        palladium_weight += self.calculate_weights(p, qty)
                        total_weight += self.calculate_weights(p, qty)
            # for line in self.big_bar_order_lines:
            #     for p in line.products:
            #         qty = float(line.total_received_quantity)
            #         if p['type'] == 'Gold':
            #             total_gold += qty
            #             total += qty
            #             gold_weight += self.calculate_weights(p, qty)
            #             total_weight += self.calculate_weights(p, qty)
            #         if p['type'] == 'Silver':
            #             total_silver += qty
            #             total += qty
            #             silver_weight += self.calculate_weights(p, qty)
            #             total_weight += self.calculate_weights(p, qty)
            #         if p['type'] == 'Platinum':
            #             total_platinum += qty
            #             total += qty
            #             platinum_weight += self.calculate_weights(p, qty)
            #             total_weight += self.calculate_weights(p, qty)
            #         if p['type'] == 'Palladium':
            #             total_palladium += qty
            #             total += qty
            #             palladium_weight += self.calculate_weights(p, qty)
            #             total_weight += self.calculate_weights(p, qty)
            temp_gold_weight = gold_weight * gold_price
            temp_silver_weight = silver_weight * silver_price
            temp_platinum_weight = platinum_weight * platinum_price
            temp_palladium_weight = palladium_weight * palladium_price
            account_value = gold_weight * gold_price + silver_weight * silver_price + platinum_weight * platinum_price + palladium_weight * palladium_price
            account_fees = 0.00
            account_fees = self.calculate_account_storage_fees(account_fees,
                                                               account_value) if account_value > 0.0 else 0.0
            customer.update({
                'total_gold': total_gold,
                'total_silver': total_silver,
                'total_platinum': total_platinum,
                'total_palladium': total_palladium,
                'total': total,
                'total_account_value': round(account_value, 2),
                'total_fees': round(account_fees, 2),
                # completed weights
                'c_gold_weight': gold_weight,
                'c_silver_weight': silver_weight,
                'c_platinum_weight': platinum_weight,
                'c_palladium_weight': palladium_weight,
                'c_total_weight': total_weight,
                'c_total_gold_value': temp_gold_weight,
                'c_total_silver_value': temp_silver_weight,
                'c_total_platinum_value': temp_platinum_weight,
                'c_total_palladium_value': temp_palladium_weight,
                'c_total_value': temp_platinum_weight + temp_palladium_weight + temp_silver_weight + temp_gold_weight
            })

    def calculate_quantity_for_existing_reports(self,customer_id,product_id,total_received_quantity):
        quantity = total_received_quantity
        order_lines = self.env['amgl.order_line'].search(
            [('customer_id', '=', customer_id),('products', '=', product_id),('is_master_records', '=', False), ('is_active', '=', True)])
        if order_lines:
            for item in order_lines:
                if item.metal_movement_id and item.metal_movement_id.state != 'completed':
                    quantity += (-item.total_received_quantity)

        return quantity

    def calculate_and_filter_existing_inventory(self,customer,date):
        gold_price, palladium_price, platinum_price, silver_price = self.get_spot_price_from_database(date)
        total_gold = total_silver = total_platinum = total_palladium = total = 0
        total_weight = gold_weight = silver_weight = platinum_weight = palladium_weight = 0
        customer_order_lines = self.get_customer_master_order_lines(customer)
        for line in customer_order_lines:
            for p in line.products:
                qty = self.calculate_quantity_for_existing_reports(customer.id,p.id,line.total_received_quantity)
                if p['type'] == 'Gold':
                    total_gold += qty
                    total += qty
                    gold_weight += self.calculate_weights(p, qty)
                    total_weight += self.calculate_weights(p, qty)
                if p['type'] == 'Silver':
                    total_silver += qty
                    total += qty
                    silver_weight += self.calculate_weights(p, qty)
                    total_weight += self.calculate_weights(p, qty)
                if p['type'] == 'Platinum':
                    total_platinum += qty
                    total += qty
                    platinum_weight += self.calculate_weights(p, qty)
                    total_weight += self.calculate_weights(p, qty)
                if p['type'] == 'Palladium':
                    total_palladium += qty
                    total += qty
                    palladium_weight += self.calculate_weights(p, qty)
                    total_weight += self.calculate_weights(p, qty)

        account_value = gold_weight * gold_price + silver_weight * silver_price + platinum_weight * platinum_price + palladium_weight * palladium_price
        account_fees = 0.00
        account_fees = self.calculate_account_storage_fees(account_fees,
                                                           account_value, customer.custodian_id.name,
                                                           customer.account_type) if account_value > 0.0 else 0.0
        return [total_weight, round(account_value, 2), round(account_fees, 2)]

    @staticmethod
    def get_spot_price_from_amark():
        url = "http://www.amark.com/feeds/spotprices?uid=DD3A01DC-A3C0-4343-9654-15982627BF5A"
        response = urllib.urlopen(url)
        data = json.loads(response.read())

        for item in data['SpotPrices']:
            if str(item['Commodity']) == 'Gold':
                Customer.gold_price = float(item['SpotAsk'])
            if str(item['Commodity']) == 'Silver':
                Customer.silver_price = float(item['SpotAsk'])
            if str(item['Commodity']) == 'Platinum':
                Customer.platinum_price = float(item['SpotAsk'])
            if str(item['Commodity']) == 'Palladium':
                Customer.palladium_price = float(item['SpotAsk'])
        return Customer.gold_price, Customer.palladium_price, Customer.platinum_price, Customer.silver_price

    @api.model
    def default_get(self, fields):
        res = super(Customer, self).default_get(fields)
        res['custodian_id'] = self.env.user.custodian_id.id
        res['grace_period_selected'] = self.get_customer_grace_period()
        return res

    def get_customer_grace_period(self):
        for item in self:
            customer = self.env['amgl.customer'].search([('id', '=', item.id)])
            if customer.grace_period:
                item.grace_period_selected = True
            else:
                item.grace_period_selected = False

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(Customer, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(res['arch'])
        for node_form in doc.xpath("//tree"):
            node_form.attrib['duplicate'] = '0'
            res['arch'] = etree.tostring(doc)
        for node_form in doc.xpath("//form"):
            doc_form = etree.XML(res['fields']['customer_order_lines2']['views']['tree']['arch'])
            for field in doc_form.xpath("//field[@name='products']"):
                if self.env.user.has_group('amgl.group_amark_admins'):
                    field.attrib['options'] = "{'no_create': False}"
                    res['fields']['customer_order_lines2']['views']['tree']['arch'] = etree.tostring(doc_form)
                else:
                    field.attrib['options'] = "{'no_create': True}"
                    res['fields']['customer_order_lines2']['views']['tree']['arch'] = etree.tostring(doc_form)
            node_form.attrib['duplicate'] = '0'
            if self.env.user.has_group('amgl.group_amark_custodian'):
                node_form.attrib['edit'] = u'0'
            res['arch'] = etree.tostring(doc)
        return res

    @api.depends("first_name", "last_name", "account_number", "account_type")
    def check_user_group(self):
        if self.first_name and self.last_name and self.account_number and self.account_type:
            self.is_o2m = True
        if self.env.user.has_group('amgl.group_amark_admins') or self.env.user.has_group('amgl.group_amark_sub_admins'):
            self.is_admin = True
            self.check_custodian_edit()
        elif self.env.user.has_group('amgl.group_amark_custodian'):
            self.is_custodian = True
        elif self.env.user.has_group('amgl.group_amark_vault'):
            self.is_vault = True
        else:
            self.is_admin = False

    def check_custodian_edit(self):
        if self.customer_order_lines:
            self.custodian_edit_not_allowed = True
        else:
            self.custodian_edit_not_allowed = False

    @api.onchange('grace_period')
    def on_change_grace_period(self):
        customer_id = self._origin.id
        if customer_id:
            customer = self.env['amgl.customer'].search([('id', '=', customer_id)])
            if customer and customer.is_grace_period_value_ever_given:
                raise ValidationError("You are changing grace period, Are you willing to proceed?")

    @api.depends("grace_period")
    def check_grace_period_edit(self):
        if self.grace_period:
            self.grace_period_selected = True
        else:
            self.grace_period_selected = False

    def _get_current_user_role(self):
        if self.env.user.has_group('amgl.group_amark_admins'):
            self.update({'user_role': 'Admin'})
        if self.env.user.has_group('amgl.group_amark_custodian'):
            self.update({'user_role': 'Custodian'})
        if self.env.user.has_group('amgl.group_amark_sub_admins'):
            self.update({'user_role': 'SubAdmin'})
        if self.env.user.has_group('amgl.group_amark_vault'):
            self.update({'user_role': 'Vault'})

    @staticmethod
    def calculate_weights(product, quantity):
        total_weight = 0.0
        if product.weight_unit == 'oz':
            total_weight = quantity * product.weight_per_piece
        if product.weight_unit == 'gram':
            total_weight = quantity * (product.weight_per_piece * 0.03215)
        if product.weight_unit == 'kg':
            total_weight = quantity * (product.weight_per_piece * 32.15)
        if product.weight_unit == 'pounds':
            total_weight = quantity * product.weight_per_piece * 16
        return total_weight

    @api.multi
    @api.depends('customer_order_lines.products', 'customer_order_lines.quantity')
    def _compute_total_by_commodity1(self):
        gold_price, palladium_price, platinum_price, silver_price = self.get_spot_price_from_amark()
        for order in self:
            total = gold = silver = platinum = palladium = 0
            total_weight = gold_weight = silver_weight = platinum_weight = palladium_weight = 0
            for line in self.customer_order_lines:
                for p in line.products:
                    qty = float(line.quantity)
                    if p['type'] == 'Gold':
                        gold += qty
                        total += qty
                        gold_weight += self.calculate_weights(p, qty)
                        total_weight += self.calculate_weights(p, qty)
                    if p['type'] == 'Silver':
                        silver += qty
                        total += qty
                        silver_weight += self.calculate_weights(p, qty)
                        total_weight += self.calculate_weights(p, qty)
                    if p['type'] == 'Platinum':
                        platinum += qty
                        total += qty
                        platinum_weight += self.calculate_weights(p, qty)
                        total_weight += self.calculate_weights(p, qty)
                    if p['type'] == 'Palladium':
                        palladium += qty
                        total += qty
                        palladium_weight += self.calculate_weights(p, qty)
                        total_weight += self.calculate_weights(p, qty)
            temp_gold_weight = gold_weight * gold_price
            temp_silver_weight = silver_weight * silver_price
            temp_platinum_weight = platinum_weight * platinum_price
            temp_palladium_weight = palladium_weight * palladium_price
            order.update({
                'total_by_commodity': gold + silver + platinum + palladium,
                'total_by_gold': gold,
                'total_by_silver': silver,
                'total_by_platinum': platinum,
                'total_by_palladium': palladium,
                'total_weight': total_weight,
                'gold_weight': gold_weight,
                'silver_weight': silver_weight,
                'platinum_weight': platinum_weight,
                'palladium_weight': palladium_weight,
                'total_weight_store': total_weight,
                'p_total_gold_value': temp_gold_weight,
                'p_total_silver_value': temp_silver_weight,
                'p_total_platinum_value': temp_platinum_weight,
                'p_total_palladium_value': temp_palladium_weight,
                'p_total_value': temp_platinum_weight + temp_palladium_weight + temp_silver_weight + temp_gold_weight
            })
        return True

    @api.model
    def create(self, vals):
        record = super(Customer, self).create(vals)
        vals['state'] = 'Created'
        if vals.get('date_opened') is None:
            date_opened = datetime.datetime.now().strftime("%Y-%m-%d")
        else:
            date_opened = vals.get('date_opened')
        self.validate_required_fields(vals)
        vals.update({
            'custodian_edit': True,
            'date_opened': date_opened
        })
        full_name = record.first_name.encode('ascii', 'ignore') + ' ' + record.last_name.encode('ascii', 'ignore')
        self.env.cr.execute(
            "UPDATE amgl_customer set full_name = '" + full_name + "' where id = " + str(record.id))
        if record['grace_period']:
            self.env.cr.execute(
                "UPDATE amgl_customer set is_grace_period_value_ever_given = '" + 'True' + "' where id = " + str(
                    record.id))
        cust_name = record['custodian_id'].name
        if self.env.user.has_group('amgl.group_amark_custodian'):

            account_number = record['account_number']
            if 'Gold' in cust_name:
                account_number = record['gst_account_number']

            template = self.env.ref('amgl.new_customer_added', raise_if_not_found=True)

            email_subject = 'Expect New IRA: ' + cust_name

            additional_email_subject_info = self.get_additional_email_subject_info()

            if additional_email_subject_info:
                email_subject = additional_email_subject_info + email_subject

            email_cc = self.env['ir.config_parameter'].get_param('email.cc')

            emails = self.get_email_for_new_customer_email(cust_name)

            template.with_context(
                custodian_name=cust_name,
                customer_name=full_name,
                account_number=account_number,
                account_type=record['account_type'],
                email_subject=email_subject,
                email_cc=email_cc,
                email_to=emails
            ).send_mail(1, force_send=False, raise_exception=False)

        current_order_lines = self.env['amgl.order_line'].search([('customer_id', '=', record['id'])])
        if current_order_lines:
            new_batch_number = (str(current_order_lines[0].id)).zfill(5)
            for item in current_order_lines:
                self.env.cr.execute(
                    "UPDATE amgl_order_line set batch_number = '" + new_batch_number + "' where id = " + str(item.id))

        return record

    def get_email_for_new_customer_email(self, cust_name):
        email_groups = self.env['amgl.email.group'].search([])
        emails = ''
        for item in email_groups:
            if cust_name in item.name:  # send emails to custodian group
                emails += ',' + item.emails
            if 'Vault Group' in item.name:  # send emails to vault group
                emails += ',' + item.emails

        emails = emails.lstrip(",")
        emails = emails.rstrip(",")
        return emails

    def get_users_for_email(self, user_groups):
        users_for_email = []
        for group in user_groups:
            self.env.cr.execute(
                "select * from res_users where id in (select uid from res_groups_users_rel where gid in (select id from res_groups where name = '" + str(
                    group) + "' ))")
            users = self.env.cr.fetchall()
            if users:
                for user in users:
                    users_for_email.append(user)
        return users_for_email

    def get_additional_email_subject_info(self):
        base_url = self.env['ir.config_parameter'].get_param('amgl.live.url')
        subject = ''
        if 'irastorage' not in base_url:
            if 'localhost' in base_url:
                subject = '(Test: Localhost) '
            elif 'odev' in base_url:
                subject = '(Test: Odev) '
        return subject

    def validate_required_fields(self, vals):
        gst_account_number = vals.get('gst_account_number')
        first_name = vals.get('first_name') if not self.first_name else self.first_name
        last_name = vals.get('last_name') if not self.last_name else self.last_name
        customer_notes = vals.get('customer_notes') if not self.customer_notes else self.customer_notes
        account_number = vals.get('account_number') if not self.account_number else self.account_number
        if self.env.user.has_group('amgl.group_amark_vault'):
            return
        if vals.get('customer_order_lines2'):
            if self.is_goldstar:
                if not vals.get('is_goldstar') and gst_account_number and not gst_account_number.strip() == '':
                    print('')
                elif gst_account_number == False or (gst_account_number and gst_account_number.strip() == ''):
                    raise ValidationError("Please Provide GoldStar Account Number.")

        if self.is_goldstar:
            if not vals.get('is_goldstar') and gst_account_number and not gst_account_number.strip() == '':
                print('')
            elif gst_account_number == False or (gst_account_number and gst_account_number.strip() == ''):
                raise ValidationError("Please Provide GoldStar Account Number.")
        if vals.get('is_goldstar'):
            if not gst_account_number or (gst_account_number and gst_account_number.strip() == ''):
                raise ValidationError("Please Provide GoldStar Account Number.")
        if first_name and "'" in first_name:
            raise ValidationError("( ' ) are not allowed in first name")
        if customer_notes and "'" in customer_notes:
            raise ValidationError("( ' ) are not allowed in special notes")
        if last_name and "'" in last_name:
            raise ValidationError("( ' ) are not allowed in last name")
        if account_number and "'" in account_number:
            raise ValidationError("( ' ) are not allowed in account number")
        if gst_account_number and "'" in gst_account_number:
            raise ValidationError("( ' ) are not allowed in goldstar account number")
        if not first_name or (first_name and first_name.strip() == ''):
            raise ValidationError("Please Provide First Name.")
        if not last_name or (last_name and last_name.strip() == ''):
            raise ValidationError("Please Provide Last Name.")
        if not account_number or (account_number and account_number.strip() == ''):
            raise ValidationError("Please Provide Account Number.")

    @api.multi
    def write(self, vals):
        if vals.get('grace_period'):
            vals.update({'is_grace_period_value_ever_given': True})
        new_products = []
        current_batch_number = uuid.uuid4()

        self.add_batch_number_to_order_line(current_batch_number, new_products, vals, 'customer_order_lines2')
        self.add_batch_number_to_order_line(current_batch_number, new_products, vals, 'big_bar_order_lines')
        record = super(Customer, self).write(vals)
        account_type = vals.get('account_type')
        account_number = vals.get('account_number')
        gst_account_number = vals.get('gst_account_number')
        if account_type or account_number or gst_account_number:
            self.update_account_info_in_withdrawal(account_type, account_number, gst_account_number)
        self.validate_required_fields(vals)
        customer_for_full_name = self.env['amgl.customer'].search([('id', '=', self.id)])
        full_name = customer_for_full_name.first_name + ' ' + customer_for_full_name.last_name
        self.env.cr.execute(
            "UPDATE amgl_customer set full_name = '" + full_name + "' where id = " + str(customer_for_full_name.id))
        current_order_lines = self.env['amgl.order_line'].search([('batch_number', '=', current_batch_number)])
        if current_order_lines:
            new_batch_number = (str(current_order_lines[0].id)).zfill(5)
            for item in current_order_lines:
                item.write({
                    'batch_number': new_batch_number
                })

        if self.env.user.has_group('amgl.group_amark_vault'):
            self.send_batch_email(new_products)
        return record

    def add_batch_number_to_order_line(self, current_batch_number, new_products, vals, field_name):
        if vals.get(field_name):
            for item in vals.get(field_name):
                if item[0] == 0:
                    item[2]['batch_number'] = current_batch_number
                    new_products.append(item)

    def update_account_info_in_withdrawal(self, account_type, account_number, gst_account_number):
        withdrawal = self.env['amgl.metal_movement'].search([('customer', '=', self.id)])
        if withdrawal:
            if account_type:
                self.env.cr.execute(
                    "UPDATE amgl_metal_movement set mmf_account_type = '" + str(
                        account_type) + "' where customer = " + str(self.id))
            if gst_account_number:
                self.env.cr.execute(
                    "UPDATE amgl_metal_movement set mmf_account_number = '" + str(
                        gst_account_number) + "' where customer = " + str(
                        self.id))
            elif account_number and 'Gold' not in self.custodian_id.name:
                self.env.cr.execute(
                    "UPDATE amgl_metal_movement set mmf_account_number = '" + str(
                        account_number) + "' where customer = " + str(
                        self.id))

    @api.multi
    def unlink(self):
        res = super(Customer, self)
        deposit_ids = []
        withdrawals_ids = []
        for item in self:
            deposit_ids.append(item.id)
        for item in self:
            withdrawals_ids.append(item.id)
        deposits = self.env['amgl.order_line'].search([('customer_id', 'in', deposit_ids)])
        withdrawals = self.env['amgl.metal_movement'].search([('customer', 'in', withdrawals_ids)])
        for deposit in deposits:
            self.env.cr.execute('DELETE FROM amgl_order_line WHERE id = ' + str(deposit.id))
        for withdrawal in withdrawals:
            self.env.cr.execute(
                "DELETE FROM amgl_metal_movement WHERE state != 'completed' and id = " + str(withdrawal.id))
        return res.unlink()

    def send_batch_email(self, new_products):

        template = self.env.ref('amgl.new_inventory_added_vault_user', raise_if_not_found=True)
        customer, customer_link = self.get_static_parameters(new_products)
        account_name = customer.full_name
        user_groups = ['Administrator', 'Sub-Admins']
        user_for_email = self.get_users_for_email(user_groups)
        deposit_date = self.customer_order_lines2[-1].date_created
        deposit_date = datetime.datetime.strptime(deposit_date, '%Y-%m-%d').strftime("%m/%d/") + deposit_date[2:4]
        product_template = self.construct_products_template(new_products)
        email_subject = str(deposit_date) + ' Deposit: #' + self.account_number
        additional_email_subject_info = self.get_additional_email_subject_info()
        if additional_email_subject_info:
            email_subject = additional_email_subject_info + email_subject
        account_number = self.account_number
        if 'Gold' in str(self.custodian_id.name):
            account_number = self.gst_account_number

        email_cc = self.env['ir.config_parameter'].get_param('email.cc')
        for user_email in user_for_email:
            mail_id = template.with_context(
                account_name=account_name,
                customer_link=customer_link,
                custodian_name=self.custodian_id.name,
                email_subject=email_subject,
                product_template=product_template,
                email_cc=email_cc,
                account_number=account_number
            ).send_mail(
                user_email[0], force_send=False, raise_exception=True)

    def get_static_parameters(self, new_products):
        base_url = self.env['ir.config_parameter'].get_param('amgl.live.url')
        customer = self.env['amgl.customer'].search([('id', '=', new_products[0][2]['customer_id'])])
        customer_menu = self.env['ir.ui.menu'].search([('name', '=', 'Customers')], limit=1)
        customer_windows_action = self.env['ir.actions.act_window'].search([('res_model', '=', 'amgl.customer')],
                                                                           limit=1)
        customer_link = base_url + "/web#id=" + str(
            self.id) + "&view_type=form&model=amgl.order_line&action=" + str(
            customer_windows_action.id) + "&menu_id=" + str(customer_menu.id)
        return customer, customer_link

    def construct_products_template(self, new_products):
        product_template = """<table   align="left" style="width:100%;padding-top:10px;padding-top:15px;border:2px  solid #7A7C7F; border-collapse: collapse;"> """
        product_template += '''
        <tr>
        <th bgcolor="#68465f" style="color:white;text-align:left;"> Product Name </th>
        <th bgcolor="#68465f" style="color:white;text-align:left;"> Product Code </th>
        <th bgcolor="#68465f" style="color:white;text-align:right;"> Quantity </th>
        <th bgcolor="#68465f" style="color:white;text-align:left;"> Weight </th>
        </tr >'''
        for new_product in new_products:
            product = self.env['amgl.products'].search([('id', '=', new_product[2]['products'])])
            product_name = product.goldstar_name
            product_code = product.gs_product_code
            # if not 'Gold' in str(self.custodian_id.name):
            #     product_name = product.name
            #     product_code = product.product_code
            total_quantity = float(new_product[2]['total_received_quantity'])
            total_weight = round(self.calculate_total_weight(product, total_quantity), 2)
            total_weight = str('{0:,.2f}'.format(total_weight))
            total_quantity = str('{0:,.0f}'.format(total_quantity))
            product_template += '''
                                      <tr>
                                          <td bgcolor="#EEEDED" style="border: 2px solid #7A7C7F;color:grey;">''' + product_name + '''</td>
                                          <td bgcolor="#EEEDED" style="border: 2px solid #7A7C7F;color:grey;">''' + product_code + '''</td>
                                          <td bgcolor="#EEEDED" style="text-align:right;border: 2px solid #7A7C7F;color:grey;">''' + total_quantity + '''</td>
                                          <td bgcolor="#EEEDED" style="text-align:right;border: 2px solid #7A7C7F;color:grey;">''' + total_weight + ''' oz.''' '''</td>
                                      </tr>'''
        return product_template + '</table>'

    def calculate_total_weight(self, product, total_quantity):
        qty = float(total_quantity)
        if product.weight_unit == 'oz':
            total_weight = qty * product.weight_per_piece
        if product.weight_unit == 'gram':
            total_weight = qty * (product.weight_per_piece * 0.03215)
        if product.weight_unit == 'kg':
            total_weight = qty * (product.weight_per_piece * 32.15)
        if product.weight_unit == 'pounds':
            total_weight = qty * product.weight_per_piece * 16
        return total_weight

    def generate_customer_code(self):
        for item in self:
            if item.custodian_id:
                if "Gold" in item.custodian_id.name:
                    if item.account_type == "Commingled":
                        item.update({
                            'amark_customer_code': 'AMV-GS1'
                        })
                    else:
                        item.update({
                            'amark_customer_code': 'AMV-GS2'
                        })

    @api.onchange('custodian_id')
    def onchange_custodian(self):
        if self.custodian_id:
            if 'Gold' in self.custodian_id.name:
                self.update({
                    'is_goldstar': True,
                })
            else:
                self.gst_account_number = None
                self.update({
                    'is_goldstar': False,
                })

    @api.one
    def _compute_o2m_field(self):
        current_activity = self.env['amgl.order_line'].search(
            [('is_master_records', '=', False), ('is_active', '=', True),
             ('customer_id', '=', self.id), ('total_received_quantity', '!=', 0)])
        if current_activity:
            self.customer_order_lines = current_activity
            return True

    def check_customer_order_lines(self, docs, custodian_name='Gold'):
        self.env.cr.execute(
            "select count(*) from amgl_order_line  o join amgl_customer c on c.id = o.customer_id where c.custodian_id in (select id from amgl_custodian where name like '%"+ custodian_name + "%') and "
            "o.is_active= True and o.total_received_quantity <> 0  and o.is_master_records = False and (c.is_account_Closed = False or c.is_account_closed is Null)")
        count = self.env.cr.fetchall()
        if count and long(count[0][0]) == 0:
            return False
        return True

    def get_activity_details(self, ol):
        order_lines = self.env['amgl.order_line'].search(
            [('products', '=', ol.products.id), ('is_master_records', '=', False),
             ('customer_id', '=', ol.customer_id.id), ('is_active', '=', True)], order='id desc')
        total_units_held = 0
        activity_date = ''
        product_activity = 0
        are_activity_details_set = False
        if order_lines:
            for item in order_lines:
                if (item.metal_movement_id.id == False or (
                        item.metal_movement_id and item.metal_movement_id.state == 'completed')):
                    total_units_held += item.total_received_quantity
                    if not are_activity_details_set:
                        activity_date = str(datetime.datetime.strptime(str(item.date_for_customer_metal_activitiy),
                                                                       '%Y-%m-%d').strftime("%m/%d/%Y"))
                        product_activity = item.total_received_quantity
                        are_activity_details_set = True
        return [total_units_held, activity_date, product_activity]

    @api.one
    def _get_completed_mmr_order_line(self):
        completed_mmr = self.env['amgl.metal_movement'].search(
            [('state', '=', 'completed'), ('customer', '=', self.id)])
        orderline_ids = []
        for mmr in completed_mmr:
            for order in mmr.order_lines:
                orderline_ids.append(order.id)

        completed_orderLines = self.env['amgl.order_line'].search(
            [('id', 'in', orderline_ids), ('customer_id', '=', self.id)])
        completed_deposit_orderLines = self.env['amgl.order_line'].search(
            [('batch_email_sent', '=', True), ('customer_id', '=', self.id)])
        batch_number_for_cmp_dpst = []
        for item in completed_deposit_orderLines:
            if not item.batch_number in batch_number_for_cmp_dpst:
                batch_number_for_cmp_dpst.append(item.batch_number)
        batch_numbers = []
        for item in completed_orderLines:
            if not item.batch_number in batch_numbers:
                batch_numbers.append(item.batch_number)
        filtered_ids = []
        for item in batch_numbers:
            filtered_ids.append(
                self.env['amgl.order_line'].search([('batch_number', '=', item), ('customer_id', '=', self.id)],
                                                   limit=1).id)
        for item in batch_number_for_cmp_dpst:
            filtered_ids.append(
                self.env['amgl.order_line'].search([('batch_number', '=', item), ('customer_id', '=', self.id)],
                                                   limit=1).id)
        self.completed_mmr = self.env['amgl.order_line'].search([('id', 'in', filtered_ids), ('is_active', '=', True)])
        return True

    @api.multi
    def cal_account_value(self):
        gold_price, palladium_price, platinum_price, silver_price = self.get_spot_price_from_amark()
        for customer in self:
            account_value = customer.gold_weight * gold_price + customer.silver_weight * silver_price + customer.platinum_weight * platinum_price + customer.palladium_weight * palladium_price
            account_fees = 0.00
            account_fees = self.calculate_account_storage_fees(account_fees,
                                                               account_value) if account_value > 0.0 else 0.0
            customer.update({
                'total_account_value': account_value,
                'total_fees': account_fees
            })

    def calculate_account_storage_fees(self, account_fees, account_value, custodian_name='', account_type=''):
        _account_type = ''
        if account_type:
            _account_type = account_type
        if 'Gold' in custodian_name:
            account_fees = self.calculate_gold_star_account_storage_fees(account_fees, account_value, _account_type)
        if 'New Direction' in custodian_name:
            account_fees = self.calculate_new_direction_account_storage_fees(account_fees, account_value, _account_type)
        if 'Provident Trust' in custodian_name:
            account_fees = self.calculate_provident_trust_account_storage_fees(account_value,_account_type)
        if 'Equity' in custodian_name:
            account_fees = self.calculate_equity_account_storage_fees(_account_type)

        return account_fees

    def calculate_equity_account_storage_fees(self, account_type):
        account_fees = 0.00
        if account_type == 'Commingled':
            account_fees = 70.00
        else:
            account_fees = 95.00
        return account_fees

    def calculate_new_direction_account_storage_fees(self, account_fees, account_value, account_type=False):
        outcome_fees = 0.0
        if account_type:
            _account_type = account_type
        else:
            _account_type = self.account_type
        if _account_type == 'Commingled':
            if 0.0 < account_value <= 50000.0:
                outcome_fees = 100.0
            elif 50000.0 < account_value <= 150000.0:
                outcome_fees = 125.0
            elif 150000.0 < account_value <= 500000.0:
                outcome_fees = 150.0
            elif account_value > 500000.0:
                outcome_fees = account_value * 0.0004  # 4 basis point

            account_fees = outcome_fees - 25.00
        else:
            outcome_fees = account_value * 0.001  # 10 basis point
            if 0.0 < outcome_fees <= 150.0:
                outcome_fees = 150.0

            two_basis_point = account_value * 0.0002
            if two_basis_point > 25.00:
                account_fees = outcome_fees - two_basis_point
            else:
                account_fees = outcome_fees - 25.00
            if account_fees < 125.0:
                account_fees = 125.0
        return account_fees

    def calculate_gold_star_account_storage_fees(self, account_fees, account_value, account_type=False):
        if account_type:
            _account_type = account_type
        else:
            _account_type = self.account_type
        if _account_type == 'Commingled':
            outcome_fees = account_value * 0.0008  # 8 basis point
            if outcome_fees > 70.0:
                account_fees = outcome_fees
            else:
                if 0 < outcome_fees < 70.0:
                    account_fees = 70.0
                else:
                    account_fees = 0.0
        else:
            outcome_fees = account_value * 0.0016  # 16 basis point
            if outcome_fees > 170.0:
                account_fees = outcome_fees
            else:
                if 0 < outcome_fees < 170.0:
                    account_fees = 170.0
                else:
                    account_fees = 0.0
        return account_fees

    def calculate_provident_trust_account_storage_fees(self,account_value, account_type=False):
        account_fees = 0.0
        if account_type:
            _account_type = account_type
        else:
            _account_type = self.account_type

        outcome_fees = 0.0
        if _account_type == 'Commingled':
            if 0.0 < account_value <= 50000.0:
                outcome_fees = 75.0
            elif 50000.0 < account_value <= 150000.0:
                outcome_fees = 100.0
            elif 150000.0 < account_value <= 500000.0:
                outcome_fees = 125.0
            elif account_value > 500000.0:
                outcome_fees = account_value * 0.0004
            account_fees = outcome_fees
        else:
            result = account_value * 0.001  # 10 basis point
            if result <= 150.0:
                account_fees = 150.00
            elif result > 150.0:
                account_fees = result * 1.00
        return account_fees

    def get_total_page_number(self, docs):
        return int(math.ceil(float(len(docs)) / 58))

    def non_segregated_round_up(self, docs):
        count = 0
        for item in docs:
            if item.account_type == 'Commingled':
                count += 1
        return int(math.ceil(float(count) / 58))

    def have_inventory_added_today(self, docs):
        todays_invenrtory_exists = False
        for order in docs.customer_order_lines:
            if order.metal_movement_id:
                if order.metal_movement_id.state == 'completed' and order.metal_movement_id.create_date == str(datetime.datetime.now().date()):
                    todays_invenrtory_exists = True
                    break
                else:
                    todays_invenrtory_exists = False
            elif not order.metal_movement_id:
                if order.date_received == str(datetime.datetime.now().date()):
                    todays_invenrtory_exists = True
                    break
                else:
                    todays_invenrtory_exists = False
        return todays_invenrtory_exists

    def custodian_name(self, docs):
        return str(docs.custodian_id.name)

    def get_init_deposit_date(self, doc):
        first_order = self.env['amgl.order_line'].search(
            [('customer_id', '=', doc.id), ('metal_movement_id', '=', False),
             ('is_master_records', '=', False)], order='date_received asc', limit=1)
        if first_order:
            first_order_month = datetime.datetime.strptime(first_order.date_received, '%Y-%m-%d').month
            first_order_year = datetime.datetime.strptime(first_order.date_received, '%Y-%m-%d').year
            return str(calendar.month_name[first_order_month]) + ", " + str(first_order_year)
        else:
            return 'N/A'

    @api.multi
    def print_report_new_direction_new_accounts_billing(self):

        previous_month = Customer.go_back_month(date.today())
        first_day = str(Customer.get_first_day(previous_month))
        last_day = str(Customer.get_last_day(previous_month))
        customers = self.env['amgl.customer'].search(
            ['&', ('is_account_closed', '=', False),('date_opened', '<=', last_day), ('date_opened', '>=', first_day)], order='account_type desc').ids
        data_object = {
            'ids': customers,
            'model': 'amgl.customer',
            'form': customers
        }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'amgl.new_direction_new_accounts_billing',
            'datas': data_object,
        }
        # report_result = self.env['report'].get_pdf(customers, 'amgl.report_customer', data=data_object)
        # attachment = self.add_report_to_attachment(report_result, 'New Accounts Billing')
        # self.upload_file(attachment,True)

    @api.multi
    def print_report_existing_accounts_billing(self):
        previous_month = Customer.go_back_month(date.today())
        first_day = str(Customer.get_first_day(previous_month))
        last_day = str(Customer.get_last_day(previous_month))
        customers = self.env['amgl.customer'].search(
            ['&', ('is_account_closed', '=', False),('date_opened', '<=', last_day), ('date_opened', '>=', first_day)], order='account_type desc').ids
        data_object = {
            'ids': customers,
            'model': 'amgl.customer',
            'form': customers
        }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'amgl.report_customer',
            'datas': data_object,
        }

    def add_report_to_attachment(self, report_result, report_name):
        attachment = self.env['ir.attachment'].create({'name': report_name,
                                                       'datas': base64.b64encode(report_result),
                                                       'datas_fname': report_name,
                                                       'res_model': 'res.users',
                                                       'res_id': 1, })
        return attachment

    @api.multi
    def view_record(self):
        self.ensure_one()
        view_id = self.env.ref('amgl.customer_form').id
        return {
            'name': 'View Record',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            "views": [[view_id, "form"]],
            'res_model': 'amgl.customer',
            'res_id': self.id,
            'target': 'fullscreen',
            'flags': {'form': {'options': {'edit': False}}},
            'context': {},
        }

    def upload_file(self, attachment, new_accounts):
        if (new_accounts):
            report_name = '' + datetime.datetime.now().strftime("%B %Y") + ' NEW ACCOUNTS BILLING.pdf'
        else:
            report_name = 'GoldStar Customer Transactions History DTC ' + datetime.datetime.now().strftime(
                "%m-%d-%Y") + '.pdf'

        if platform.system() == 'Linux':
            filestore_path = '/home/ahsan/.local/share/Odoo/filestore/' + self._cr.dbname + '/'
        else:
            filestore_path = 'C:/Users/ahsana/AppData/Local/OpenERP S.A/Odoo/filestore/' + self._cr.dbname + '/'

        session = ftplib.FTP('mehmood.allshoreresources.com', 'mehmood', '@PasswordMU')
        file = open(filestore_path + attachment.store_fname, 'rb')  # file to send
        session.storbinary('STOR ./Test Ahsan/' + report_name, file)  # send the file
        file.close()  # close file and FTP
        session.quit()

    def print_report_customer_activity(self):
        custodian = self.env['amgl.custodian'].search([('name', 'ilike', 'Gold')], limit=1)
        customers = self.env['amgl.customer'].search([('is_account_closed', '=', False),('custodian_id', '=', custodian.id)]).ids
        data_object = {
            'ids': customers,
            'model': 'amgl.customer',
            'form': customers
        }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'amgl.customer_full_activity_report',
            'datas': data_object,
        }
        report_result = self.env['report'].get_pdf(customers, 'amgl.customer_full_activity_report', data=data_object)
        attachment = self.add_report_to_attachment(report_result, 'GoldStar Customer Transactions History')
        self.upload_file(attachment, False)

    def print_report_customer_daily_activity(self):
        custodian = self.env['amgl.custodian'].search([('name', 'ilike', 'Gold')], limit=1)
        customers = self.env['amgl.customer'].search([('is_account_closed', '=', False),('custodian_id', '=', custodian.id)])
        filtered_customers = []
        filter_ids = []
        for customer in customers:
            orders = self.env['amgl.order_line'].search(
                ['&', ('customer_id', '=', customer.id), ('date_created', '=', datetime.datetime.now().date())])

            if orders:
                filtered_customers.append(customer)
        for fc in filtered_customers:
            filter_ids.append(fc.id)

        data_object = {
            'ids': filter_ids,
            'model': 'amgl.customer',
            'form': filter_ids
        }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'amgl.customer_daily_transaction_report',
            'datas': data_object,
        }
        report_result = self.env['report'].get_pdf(filtered_customers_ids, 'amgl.customer_daily_transaction_report',
                                                   data=data_object)
        attachment = self.add_report_to_attachment(report_result, 'GoldStar Customer Transactions History')
        self.upload_file(attachment, False)

    def print_report_customer_current_inventory(self):
        custodian = self.env['amgl.custodian'].search([('name', 'ilike', 'Gold')], limit=1)
        customers = self.env['amgl.customer'].search([('is_account_closed', '=', False),('custodian_id', '=', custodian.id)])
        filtered_customers = []
        filter_ids = []
        for customer in customers:
            orders = self.env['amgl.order_line'].search(
                ['&', ('customer_id', '=', customer.id), ('total_received_quantity', '>', 0)])
            if orders:
                filtered_customers.append(customer)
        for fc in filtered_customers:
            filter_ids.append(fc.id)

        data_object = {
            'ids': filter_ids,
            'model': 'amgl.customer',
            'form': filter_ids
        }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'amgl.report_customer_current_inventory',
            'datas': data_object,
        }

    def print_single_report_customer_current_inventory(self):
        if len(self) == 1:
            customers = self.env['amgl.customer'].search([('is_account_closed', '=', False),('id', '=', self.id)])
        if len(self) > 1:
            customers = self.env['amgl.customer'].search([('is_account_closed', '=', False),('id', 'in', self.ids)])
        filtered_customers = []
        filter_ids = []
        for customer in customers:
            orders = self.env['amgl.order_line'].search(
                ['&', ('customer_id', '=', customer.id), ('total_received_quantity', '>', 0)])
            if orders:
                filtered_customers.append(customer)
        for fc in filtered_customers:
            filter_ids.append(fc.id)
        if len(filter_ids) == 0:
            raise ValidationError('Not sufficient data for reporting. ')
        data_object = {
            'ids': filter_ids,
            'model': 'amgl.customer',
            'form': filter_ids
        }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'amgl.report_customer_current_inventory',
            'datas': data_object,
        }

    def print_report_customer_metal_activity(self):
        custodian = self.env['amgl.custodian'].search([('name', 'ilike', 'Gold')], limit=1)
        customers = self.env['amgl.customer'].search([('custodian_id', '=', custodian.id)])
        filtered_customers = []
        filter_ids = []
        for customer in customers:
            orders = self.env['amgl.order_line'].search(
                ['&', ('customer_id', '=', customer.id), ('total_received_quantity', '>', 0)],
                order="date_received asc")
            if orders:
                filtered_customers.append(customer)
        for fc in filtered_customers:
            filter_ids.append(fc.id)

        data_object = {
            'ids': filter_ids,
            'model': 'amgl.customer',
            'form': filter_ids
        }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'amgl.report_customer_metal_activity',
            'datas': data_object,
        }

    def getFormattedDate(self):
        return datetime.datetime.now(pytz.timezone('US/Pacific')).strftime('%m/%d/%Y')

    def get_sorted_list(self, obj_list, sort_by_product_code=False, sort_by_product_id=False):
        if sort_by_product_code:
            return obj_list.sorted(key=lambda x: x.gs_product_code, reverse=False)
        elif sort_by_product_id:
            return obj_list.sorted(key=lambda x: x.id, reverse=False)
        else:
            return obj_list.sorted(key=lambda x: x.date_for_customer_metal_activitiy, reverse=True)

    def get_date1(self):
        todays_date = datetime.datetime.now().strftime("%m-%d-%y")
        month_name = calendar.month_name[int(todays_date[:2])]
        final_date = month_name + ' ' + str(datetime.datetime.now().day) + ',' + str(datetime.datetime.now().year)
        return final_date

    def get_date2(self):
        return str(datetime.datetime.now().month) + '/' + str(datetime.datetime.now().day) + '/' + str(
            datetime.datetime.now().year)

    def get_unit_total(self, order_line_list, product_code):
        u_total = 0
        for order in order_line_list:
            if order.products.product_code == product_code:
                u_total += order.total_received_quantity
        return u_total

    def get_order_line_obj(self, obj_id):
        return self.env['amgl.order_line'].browse(obj_id)

    def check_account_type_group(self):
        if self.env.user.has_group('amgl.group_amark_sub_admins'):
            self.account_type_restricted_group = True
        elif self.env.user.has_group('amgl.group_amark_admins'):
            self.account_type_restricted_group = False
        elif self.env.user.has_group('amgl.group_amark_custodian'):
            self.state = 'Created'
            self.account_type_restricted_group = True
        elif self.env.user.has_group('amgl.group_amark_vault'):
            self.account_type_restricted_group = True

    def check_account_type_change_access(self):
        if self.env.user.has_group('amgl.group_amark_admins'):
            self.allow_account_type_change = True
        else:
            self.allow_account_type_change = False

    def automated_action_method(self):
        active_ids = self._context.get('active_ids')
        for active_id in active_ids:
            user = self.env['res.users'].search([('id', '=', active_id)])
            if user.has_group('amgl.group_amark_authorizer') or user.has_group('amgl.group_amark_vault'):
                mmr_windows_action = self.env['ir.actions.act_window'].search(
                    [('res_model', '=', 'amgl.metal_movement')],
                    limit=1)
                user.write({
                    'action_id': mmr_windows_action.id
                })
            else:
                account_action = self.env['ir.actions.act_window'].search(
                    [('res_model', '=', 'amgl.customer')],
                    limit=1)
                user.write({
                    'action_id': account_action.id
                })

    #region Full Inventory Report Excel

    def download_full_inventory_report(self):
        file_name = '/excel/Master_IRA Storage Account Tracker.xlsx'
        bold, red_text, underline, workbook, worksheet = self.configure_workbook_for_full_excel_report(file_name)
        merge_cell_format_heading = workbook.add_format({'align': 'center', 'bold': True})
        right_align = workbook.add_format({'align': 'right'})
        red_text_right_align = workbook.add_format({'font_color': 'red', 'align': 'right'})
        total_holding_format = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': 'skyblue',
            'font_color': 'black'
        })
        self.add_full_excel_report_headers(bold, worksheet, merge_cell_format_heading, total_holding_format)
        worksheet.autofilter(0, 0, 500000, 16)
        row_count = 1
        column_count = 0
        all_customers = self.env['amgl.customer'].search([('is_account_closed', '=', False)])
        for customer in all_customers:
            all_order_lines = self.env['amgl.order_line'].search(
                [('customer_id', '=', customer.id), ('is_active', '!=', False), ('is_master_records', '=', False)])
            total_weight = 0
            for order in all_order_lines:
                total_weight += order.temp_received_weight
                if order.metal_movement_id:
                    if order.metal_movement_id.state == 'completed':
                        self.add_withdraw_line(column_count, customer, order, red_text, row_count, worksheet,
                                               red_text_right_align)
                        row_count += 1
                        column_count = 0
                else:
                    self.add_deposit_line(column_count, customer, order, row_count, worksheet, right_align)
                    row_count += 1
                    column_count = 0
        workbook.close()
        attachment_id = self.add_file_in_attachment(file_name).id
        base_url = self.env['ir.config_parameter'].get_param('amgl.live.url')
        return {
            'type': 'ir.actions.act_url',
            'url': base_url + '/web/content/%s/%s' % (attachment_id, file_name.replace('/excel/', '')),
            'target': 'self'
        }

    def configure_workbook_for_full_excel_report(self, file_name):
        workbook = xlsxwriter.Workbook(file_name)
        worksheet = workbook.add_worksheet('NDIRA Inventory')
        bold = workbook.add_format({'bold': True})
        underline = workbook.add_format({'underline': True})
        red_text = workbook.add_format({'font_color': 'red'})
        merge_format = workbook.add_format({
            'bold': 1,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': 'white',
            'font_color': 'black'
        })
        return bold, red_text, underline, workbook, worksheet

    def add_full_excel_report_headers(self, bold, worksheet, merge_cell_format_heading, total_holding_format):

        # Insert Headers for table
        worksheet.write('A1', 'Custodian', bold)
        worksheet.write('B1', 'Last Name', bold)
        worksheet.write('C1', 'First Name', bold)
        worksheet.write('D1', 'Account Number', bold)
        worksheet.write('E1', 'Account Type', bold)
        worksheet.write('F1', 'Date Opened', bold)
        worksheet.write('G1', 'Date Received', bold)
        worksheet.write('H1', 'Commodity', bold)
        worksheet.write('I1', 'Qty', bold)
        worksheet.write('J1', 'Weight', bold)
        worksheet.write('K1', 'Product Description', bold)
        worksheet.write('L1', 'Total Weight', bold)
        worksheet.write('M1', 'Total Value', bold)

    @staticmethod
    def add_deposit_line(column_count, customer, order, row_count, worksheet, right_align):
        dt_open = datetime.datetime.strptime(str(customer.date_opened), '%Y-%m-%d')
        date_opened = '{0}/{1}/{2:02}'.format(dt_open.month, dt_open.day, dt_open.year % 100)
        dt_receive = datetime.datetime.strptime(str(order.date_received), '%Y-%m-%d')
        account_value = Customer.calculate_current_orderline_value(order)
        weight_per_piece = Customer.calculate_weights(order.products, 1)
        date_received = '{0}/{1}/{2:02}'.format(dt_receive.month, dt_receive.day, dt_receive.year % 100)
        worksheet.write(row_count, column_count, customer.custodian_id.name)
        column_count += 1
        worksheet.write(row_count, column_count, customer.last_name)
        column_count += 1
        worksheet.write(row_count, column_count, customer.first_name)
        column_count += 1
        worksheet.write(row_count, column_count,
                        customer.account_number if 'Gold' not in customer.custodian_id.name else customer.gst_account_number)
        column_count += 1
        worksheet.write(row_count, column_count, customer.account_type)
        column_count += 1
        worksheet.write(row_count, column_count, date_opened)
        column_count += 1
        worksheet.write(row_count, column_count, date_received)
        column_count += 1
        worksheet.write(row_count, column_count, order.products.type)
        column_count += 1
        worksheet.write(row_count, column_count, order.total_received_quantity)
        column_count += 1
        worksheet.write(row_count, column_count, str('{0:,.2f}'.format(weight_per_piece)) + ' oz.', right_align)
        column_count += 1
        worksheet.write(row_count, column_count, order.products.goldstar_name)
        column_count += 1
        worksheet.write(row_count, column_count, str('{0:,.2f}'.format(order.temp_received_weight)) + ' oz.',
                        right_align)
        column_count += 1
        worksheet.write(row_count, column_count, '$' + str('{0:,.2f}'.format(account_value)))
        column_count += 1

    @staticmethod
    def calculate_current_orderline_value(order):
        gold_price, palladium_price, platinum_price, silver_price = Customer.get_spot_price_from_amark()
        account_value = 0
        if order.products.type == 'Gold':
            account_value = order.total_received_quantity * gold_price
        if order.products.type == 'Silver':
            account_value = order.total_received_quantity * silver_price
        if order.products.type == 'Platinum':
            account_value = order.total_received_quantity * platinum_price
        if order.products.type == 'Palladium':
            account_value = order.total_received_quantity * palladium_price
        return account_value

    @staticmethod
    def add_withdraw_line(column_count, customer, order, red_text, row_count, worksheet, red_text_right_align):
        dt_open = datetime.datetime.strptime(str(customer.date_opened), '%Y-%m-%d')
        date_opened = '{0}/{1}/{2:02}'.format(dt_open.month, dt_open.day, dt_open.year % 100)
        dt_create = datetime.datetime.strptime(order.metal_movement_id.date_create, '%Y-%m-%d')
        date_create = '{0}/{1}/{2:02}'.format(dt_create.month, dt_create.day, dt_create.year % 100)
        account_value = Customer.calculate_current_orderline_value(order)
        weight_per_piece = Customer.calculate_weights(order.products, 1)
        worksheet.write(row_count, column_count, customer.custodian_id.name, red_text)
        column_count += 1
        worksheet.write(row_count, column_count, customer.last_name, red_text)
        column_count += 1
        worksheet.write(row_count, column_count, customer.first_name, red_text)
        column_count += 1
        worksheet.write(row_count, column_count,
                        customer.account_number if 'Gold' not in customer.custodian_id.name else customer.gst_account_number,
                        red_text)
        column_count += 1
        worksheet.write(row_count, column_count, customer.account_type, red_text)
        column_count += 1
        worksheet.write(row_count, column_count, date_opened, red_text)
        column_count += 1
        worksheet.write(row_count, column_count, date_create, red_text)
        column_count += 1
        worksheet.write(row_count, column_count, order.products.type, red_text)
        column_count += 1
        worksheet.write(row_count, column_count, order.total_received_quantity, red_text)
        column_count += 1
        worksheet.write(row_count, column_count, str('{0:,.2f}'.format(weight_per_piece)) + ' oz.',
                        red_text_right_align)
        column_count += 1
        worksheet.write(row_count, column_count, order.products.goldstar_name, red_text)
        column_count += 1
        worksheet.write(row_count, column_count, str('{0:,.2f}'.format(order.temp_received_weight)) + ' oz.',
                        red_text_right_align)
        column_count += 1
        worksheet.write(row_count, column_count, '', red_text)
        column_count += 1

    def add_file_in_attachment(self, file_name):
        byte_data = 0
        with open(file_name, "rb") as xlfile:
            byte_data = xlfile.read()
        attachment = self.env['ir.attachment'].create({'name': file_name,
                                                       'datas': base64.b64encode(byte_data),
                                                       'datas_fname': file_name,
                                                       'res_model': 'res.users',
                                                       'res_id': 1, })
        return attachment


    #endregion


    def get_custodians_only(self):
        custodians = self.env['amgl.custodian'].search([])
        result = []
        for item in custodians:
            result.append(item.name)
        return result

    def get_custodians(self, docs):
        custodians = []
        for item in docs:
            custodians.append(item.custodian_id.name)
        return list(set(custodians))

    def get_products(self, type):
        products = self.env['amgl.products'].search([('type', '=', type)])
        product_names = []
        for item in products:
            product_names.append(item.goldstar_name)

        product_names = list(dict.fromkeys(product_names))
        product_names = sorted(product_names)
        return product_names

    def get_products_details(self, product, custodian, account_type):
        _product = self.env['amgl.products'].search([('goldstar_name', '=', product)], limit=1)
        _custodian = self.env['amgl.custodian'].search([('name', '=', custodian)])
        customers = self.env['amgl.customer'].search(
            [('is_account_closed', '=', False),('custodian_id', '=', _custodian.id), ('account_type', '=', account_type)]).ids
        order_lines = self.env['amgl.order_line'].search(
            [('products', '=', _product.id), ('is_master_records', '=', True), ('customer_id', 'in', customers)])
        total_quantity = 0
        for item in order_lines:
            total_quantity += self.get_total_quantity_after_including_completed_withdrawal(item)

        return [_product.product_code, _product.goldstar_name, total_quantity, _product.weight_per_piece,
                _product.weight_per_piece * total_quantity, _product.weight_unit]

    def get_total_weight(self, customer, date):
        gold_weight, palladium_weight, platinum_weight, silver_weight = self.get_total_weight_for_new_accounts_report(
            customer, date)
        return gold_weight + silver_weight + platinum_weight + palladium_weight

    def get_account_value(self, customer, date):
        gold_weight, palladium_weight, platinum_weight, silver_weight = self.get_total_weight_for_new_accounts_report(
            customer, date)

        gold_price, palladium_price, platinum_price, silver_price = self.get_spot_price_from_database(date)
        account_value = gold_weight * gold_price + silver_weight * silver_price + platinum_weight * platinum_price \
                        + palladium_weight * palladium_price
        return account_value

    def get_total_weight_for_new_accounts_report(self, customer, date):
        month = datetime.datetime.strptime(str(date.split(',')[0]), '%B').month
        year = int(date.split(',')[1])
        start_date = datetime.datetime(int(year), int(month), 1)
        if int(month) < 12:
            end_date = datetime.datetime(int(year), int(month) + 1, 1) - relativedelta(days=1)
        else:
            end_date = datetime.datetime(int(year), int(month), 31)
        customer_order_lines = self.env['amgl.order_line'].search(
            [('customer_id', '=', customer.id), ('date_received', '>=', start_date), ('is_master_records', '=', False)], order='date_received asc')
        gold_weight = 0
        silver_weight = 0
        platinum_weight = 0
        palladium_weight = 0
        filtered_customer_order_lines = []
        for item in customer_order_lines:
            if item.metal_movement_id:
                if item.metal_movement_id.state == 'completed':
                    filtered_customer_order_lines.append(item)
            else:
                filtered_customer_order_lines.append(item)

        for item in filtered_customer_order_lines:
            if item.products.type == 'Gold':
                gold_weight += self.calculate_weights(item.products, item.total_received_quantity)
            if item.products.type == 'Silver':
                silver_weight += self.calculate_weights(item.products, item.total_received_quantity)
            if item.products.type == 'Platinum':
                platinum_weight += self.calculate_weights(item.products, item.total_received_quantity)
            if item.products.type == 'Palladium':
                palladium_weight += self.calculate_weights(item.products, item.total_received_quantity)
        return gold_weight, palladium_weight, platinum_weight, silver_weight

    def get_spot_price_from_database(self, date):
        month = str(date.split(',')[0])
        year = int(date.split(',')[1])

        spot_price_object = self.env['amgl.closing.rates'].search(
            [('month', '=', month), ('years', '=', year)])
        return spot_price_object.gold_rate, spot_price_object.palladium_rate, \
               spot_price_object.platinum_rate, spot_price_object.silver_rate

    def get_account_fees(self, customer, date):
        gold_weight, palladium_weight, platinum_weight, silver_weight = self.get_total_weight_for_new_accounts_report(
            customer, date)

        gold_price, palladium_price, platinum_price, silver_price = self.get_spot_price_from_database(date)
        account_value = gold_weight * gold_price + silver_weight * silver_price + platinum_weight * platinum_price \
                        + palladium_weight * palladium_price
        account_fees = 0.00
        if 'Gold' in customer.custodian_id.name:
            if customer.account_type == 'Commingled':
                outcome_fees = account_value * 0.0008  # 8 basis point
                if outcome_fees > 70.0:
                    account_fees = outcome_fees
                else:
                    if 0 < outcome_fees < 70.0:
                        account_fees = 70.0
                    else:
                        account_fees = 0.0
            else:
                outcome_fees = account_value * 0.0016  # 16 basis point
                if outcome_fees > 170.0:
                    account_fees = outcome_fees
                else:
                    if 0 < outcome_fees < 170.0:
                        account_fees = 170.0
                    else:
                        account_fees = 0.0
                        
        if 'Provident' in customer.custodian_id.name:
            outcome_fees = 0.0
            if customer.account_type == 'Commingled':
                if 0.0 < account_value <= 50000.0:
                    outcome_fees = 75.0
                elif 50000.0 < account_value <= 150000.0:
                    outcome_fees = 100.0
                elif 150000.0 < account_value <= 500000.0:
                    outcome_fees = 125.0
                elif account_value > 500000.0:
                    outcome_fees = account_value * 0.0004
                account_fees = outcome_fees
            else:
                result = account_value * 0.001  # 10 basis point
                if result <= 150.0:
                    account_fees = 150.00
                elif result > 150.0:
                    account_fees = result * 1.00

        if 'New Direction' in customer.custodian_id.name:
            outcome_fees = 0.0
            if customer.account_type == 'Commingled':
                if 0.0 < account_value <= 50000.0:
                    outcome_fees = 100.0
                elif 50000.0 < account_value <= 150000.0:
                    outcome_fees = 125.0
                elif 150000.0 < account_value <= 500000.0:
                    outcome_fees = 150.0
                elif account_value > 500000.0:
                    outcome_fees = account_value * 0.0004  # 4 basis point

                two_basis_point = account_value * 0.0002
                if two_basis_point > 25.00:
                    account_fees = outcome_fees - two_basis_point
                else:
                    account_fees = outcome_fees - 25.00
            else:
                outcome_fees = account_value * 0.001  # 10 basis point
                if 0.0 < outcome_fees <= 150.0:
                    outcome_fees = 150.0

                two_basis_point = account_value * 0.0002
                if two_basis_point > 25.00:
                    account_fees = outcome_fees - two_basis_point
                else:
                    account_fees = outcome_fees - 25.00
                if account_fees < 125.0:
                    account_fees = 125.0

        if 'Equity' in str(customer.custodian_id.name):
            if customer.account_type == 'Commingled':
                account_fees = 70.00
            else:
                account_fees = 95.00

        return account_fees

    def get_products_for_combined_holding_statement(self, type, custodian='Gold'):
        products = self.env['amgl.products'].search([('type', '=', type)], order='gs_product_code asc')
        filtered_products = []
        custodian_customers_ids = self.get_customer_ids(False, custodian)
        if len(custodian_customers_ids) > 0:
            for product in products:
                orders = self.env['amgl.order_line'].search(
                    [('products', '=', product.id), ('metal_movement_id', '=', False), ('is_master_records', '=', True),
                     ('customer_id', 'in', custodian_customers_ids)])
                total_quantity = 0.00
                for order in orders:
                    total_quantity += order.total_received_quantity

                withdrawals = self.env['amgl.order_line'].search(
                    [('products', '=', product.id), ('metal_movement_id', '!=', False),
                     ('is_master_records', '=', False),
                     ('customer_id', 'in', custodian_customers_ids)])
                for item in withdrawals:
                    if item.metal_movement_id.state != 'completed':
                        total_quantity += float(item.quantity)

                if total_quantity > 0:
                    filtered_products.append(product)

        return filtered_products

    def get_customer_ids(self, account_type=False, custodian_name='Gold'):
        custodian_id = self.env['amgl.custodian'].search([('name', 'ilike', custodian_name)]).id
        if account_type:
            custodian_customers = self.env['amgl.customer'].search(
                [('custodian_id', '=', custodian_id), ('is_account_closed', '=', False),  ('account_type', '=', account_type)])
        else:
            custodian_customers = self.env['amgl.customer'].search([('is_account_closed', '=', False), ('custodian_id', '=', custodian_id)])
        custodian_customers_ids = []
        for item in custodian_customers:
            custodian_customers_ids.append(item.id)
        return custodian_customers_ids

    def get_product_count_for_combined_holding_statement(self, product, account_type, custodian_name='Gold'):
        custodian_customers_ids = self.get_customer_ids(account_type, custodian_name)
        orders = self.env['amgl.order_line'].search(
            [('products', '=', product.id), ('metal_movement_id', '=', False), ('is_master_records', '=', True),
             ('customer_id', 'in', custodian_customers_ids)])
        total_quantity = 0.00
        for order in orders:
            total_quantity += order.total_received_quantity

        withdrawals = self.env['amgl.order_line'].search(
            [('products', '=', product.id), ('metal_movement_id', '!=', False), ('is_master_records', '=', False),
             ('customer_id', 'in', custodian_customers_ids)])
        for item in withdrawals:
            if item.metal_movement_id.state != 'completed':
                total_quantity += float(item.quantity)

        return total_quantity

    def get_customers_against_product(self, product, custodian_name='Gold'):
        order_lines = self.env['amgl.order_line'].search(
            [('products', '=', product.id), ('is_master_records', '=', True), ('metal_movement_id', '=', False)])
        customer_ids = []
        for order in order_lines:
            if custodian_name in order.customer_id.custodian_id.name:
                customer_ids.append(order.customer_id.id)
        customer_ids = list(set(customer_ids))  # removing duplicates
        return self.env['amgl.customer'].search([('id', 'in', customer_ids), ('is_account_closed', '=', False)], order='last_name asc')

    def get_customer_info_for_combined_holding_by_customer(self, customer, product):
        customer = self.env['amgl.customer'].search([('id', '=', customer.id), ('is_account_closed', '=', False)])
        order_lines = self.env['amgl.order_line'].search(
            [('products', '=', product.id), ('is_master_records', '=', True), ('metal_movement_id', '=', False),
             ('customer_id', '=', customer.id)])
        total_quantity = 0
        for order in order_lines:
            total_quantity += order.total_received_quantity

        withdrawals = self.env['amgl.order_line'].search(
            [('products', '=', product.id), ('metal_movement_id', '!=', False), ('is_master_records', '=', False),
             ('customer_id', '=', customer.id)])
        for item in withdrawals:
            if item.metal_movement_id.state != 'completed':
                total_quantity += float(item.quantity)
        if total_quantity > 0:
            first_column = customer.last_name + ', ' + (customer.gst_account_number if 'Gold' in customer.custodian_id.name else customer.account_number)
            second_column = customer.full_name
            third_column = (customer.gst_account_number if 'Gold' in customer.custodian_id.name else customer.account_number)
            fourth_column = total_quantity if customer.account_type == 'Segregated' else 0.00
            fifth_column = total_quantity if customer.account_type == 'Commingled' else 0.00

            return [first_column, second_column, third_column, fourth_column, fifth_column]
        return False

    def get_customer_for_fair_value_report(self,custodian):
        custodian_id = self.env['amgl.custodian'].search(
            [('name', 'ilike', custodian)]).id  # Fetch custodian
        gst_customers = self.env['amgl.customer'].search([('is_account_closed', '=', False), ('custodian_id', '=', custodian_id)],
                                                         order='last_name asc')  # Fetch all customers
        filtered_customers = []  # Add all customers against which order_lines exists
        for customer in gst_customers:
            order_lines = self.env['amgl.order_line'].search(
                [('customer_id', '=', customer.id), ('is_master_records', '=', True),
                 ('metal_movement_id', '=', False)])

            for item in order_lines:
                deposit, withdrawal = self.get_deposits_and_withdrawals_against_product_id(customer, item.products.id)
                quantity = deposit.total_received_quantity
                quantity = self.include_non_completed_withdrawal_quantity(quantity, withdrawal)
                if quantity > 0:
                    filtered_customers.append(customer.id)

        return self.env['amgl.customer'].search([('is_account_closed', '=', False), ('id', 'in', filtered_customers)])

    def get_customer_products_for_fair_value_report(self, customer):
        customer_product_ids = self.get_product_ids_against_customer_id(customer)
        customer_info = []
        quantity = 0
        for product_id in customer_product_ids:
            deposit, withdrawal = self.get_deposits_and_withdrawals_against_product_id(customer, product_id)
            quantity = deposit.total_received_quantity
            quantity = self.include_non_completed_withdrawal_quantity(quantity, withdrawal)
            total_ounces = self.get_product_ounces(deposit.products, quantity)
            if quantity > 0:
                fair_value_per_unit = 0.0
                per_piece_weight = total_ounces / quantity
                gold_price, palladium_price, platinum_price, silver_price = self.get_spot_price_from_amark()
                if deposit.products.type == 'Gold':
                    fair_value_per_unit = per_piece_weight * gold_price
                if deposit.products.type == 'Silver':
                    fair_value_per_unit = per_piece_weight * silver_price
                if deposit.products.type == 'Platinum':
                    fair_value_per_unit = per_piece_weight * platinum_price
                if deposit.products.type == 'Palladium':
                    fair_value_per_unit = per_piece_weight * palladium_price
                customer_info.append(
                    deposit.products.gs_product_code + '|' + deposit.products.goldstar_name + '|' + str(
                        quantity) + '|' + str(fair_value_per_unit))
        return customer_info

    def get_product_ids_against_customer_id(self, customer):
        order_lines = self.env['amgl.order_line'].search(
            [('customer_id', '=', customer.id), ('is_master_records', '=', True),
             ('metal_movement_id', '=', False)])
        customer_product_ids = []
        for item in order_lines:
            if item.products not in customer_product_ids:
                customer_product_ids.append(item.products.id)
        return customer_product_ids

    @staticmethod
    def include_non_completed_withdrawal_quantity(quantity, withdrawal):
        for item in withdrawal:
            if item.metal_movement_id.state != 'completed':
                quantity += float(item.quantity)
        return quantity

    def get_deposits_and_withdrawals_against_product_id(self, customer, product_id):
        order_line = self.env['amgl.order_line'].search(
            [('customer_id', '=', customer.id), ('is_master_records', '=', True), ('products', '=', product_id),
             ('metal_movement_id', '=', False)])
        withdrawal_order_line = self.env['amgl.order_line'].search(
            [('customer_id', '=', customer.id), ('products', '=', product_id), ('total_received_quantity', '<', 0)])
        return order_line, withdrawal_order_line

    def get_product_ounces(self, product, quantity):
        product = self.env['amgl.products'].search([('id', '=', product.id)])
        qty = float(quantity)
        if product.weight_unit == 'oz':
            total_weight = qty * product.weight_per_piece
        if product.weight_unit == 'gram':
            total_weight = qty * (product.weight_per_piece * 0.03215)
        if product.weight_unit == 'kg':
            total_weight = qty * (product.weight_per_piece * 32.15)
        if product.weight_unit == 'pounds':
            total_weight = qty * product.weight_per_piece * 16
        return total_weight

    def get_ols_for_customer_position_listing(self, customer):
        customer_metal_activity_ol = customer.customer_order_lines
        unique_products = []
        filtered_ol_ids = []
        order_lines = []
        if customer_metal_activity_ol:
            for ol in customer_metal_activity_ol:
                if not ol.products.id in unique_products:
                    unique_products.append(ol.products.id)
            for product_id in unique_products:
                sorted_products = filter(lambda x: (x.products.id == product_id), customer_metal_activity_ol)
                total_quantity = 0
                if sorted_products:
                    for item in sorted_products:
                        if (item.metal_movement_id.id == False or (
                                    item.metal_movement_id and item.metal_movement_id.state == 'completed')):
                            total_quantity += item.total_received_quantity
                    if total_quantity > 0:
                        filtered_ol_ids.append(product_id)
                if filtered_ol_ids:
                    order_lines = self.env['amgl.order_line'].search([('is_active', '=', True),
                                                                      ('products', 'in', filtered_ol_ids),
                                                                      ('is_master_records', '=', True),
                                                                      ('customer_id', '=', customer.id)])
        return order_lines

    def check_header_details_for_font_compatibility(self, customer):
        account_number = ''
        if 'Gold' in customer.custodian_id.name:
            if customer:
                if len(str(customer.last_name + customer.gst_account_number)) > 27 or len(
                        str(customer.full_name + customer.gst_account_number)) > 45 or len(
                    str(customer.gst_account_number)) > 11 or len(str(customer.account_number)) > 11:
                    return False
        if 'Provident' in customer.custodian_id.name:
            if customer:
                if len(str(customer.last_name + customer.account_number)) > 27 or len(
                        str(customer.full_name + customer.account_number)) > 45 or len(
                    str(customer.gst_account_number)) > 11 or len(str(customer.account_number)) > 11:
                    return False
        return True

    def get_filtered_customer_order_lines(self):
        order_lines = self.env['amgl.order_line'].search([('is_master_records', '=', False),('customer_id', '=', self.id),('is_active', '=', True)])
        filtered_order_lines = []
        if order_lines:
            sorted_order_lines = self.get_sorted_list(order_lines)
            for item in sorted_order_lines:
                if not item.metal_movement_id or (item.metal_movement_id and item.metal_movement_id.state == 'completed'):
                    filtered_order_lines.append(item)
        return filtered_order_lines

    def get_total_quantity_after_including_completed_withdrawal(self, order):
        master_product_quantity = order.total_received_quantity
        order_lines = self.env['amgl.order_line'].search(
            [('products', '=', order.products.id), ('is_master_records', '=', False), ('customer_id', '=', order.customer_id.id)])
        if order_lines:
            for item in order_lines:
                if item.metal_movement_id and item.metal_movement_id.state != 'completed' and item.metal_movement_id.mmr_number:
                    master_product_quantity += (-item.total_received_quantity)
        return master_product_quantity

    def get_total_weight_after_including_completed_withdrawal(self, order):
        master_product_quantity = order.temp_received_weight
        order_lines = self.env['amgl.order_line'].search(
            [('products', '=', order.products.id), ('is_master_records', '=', False), ('customer_id', '=', order.customer_id.id)])
        if order_lines:
            for item in order_lines:
                if item.metal_movement_id and item.metal_movement_id.state != 'completed' and item.metal_movement_id.mmr_number:
                    master_product_quantity += (-item.temp_received_weight)
        return master_product_quantity

    def get_order_lines_for_customer_current_inventory(self, customer):
        order_lines = self.env['amgl.order_line'].search([('customer_id', '=', customer.id)])
        filtered_order_lines = []
        all_withdrawn = self.check_if_all_quantity_is_withdrawn(customer)
        if all_withdrawn:
            return filtered_order_lines

        for item in order_lines:
            if item.metal_movement_id:
                if item.metal_movement_id.state == 'completed':
                    filtered_order_lines.append(item)
            else:
                if item.is_master_records:
                    filtered_order_lines.append(item)
        return filtered_order_lines

    def get_customer_master_order_lines(self, customer):
        customer_master_order_lines = self.env['amgl.order_line'].search([('customer_id', '=', customer.id),
                                                                          ('is_master_records', '=', True),
                                                                          ('is_active', '=', True)])
        filtered_order_lines = []
        if customer_master_order_lines:
            for order_line in customer_master_order_lines:
                master_product_quantity = self.get_total_quantity_after_including_completed_withdrawal(order_line)
                if master_product_quantity > 0:
                    filtered_order_lines.append(order_line)
        return filtered_order_lines

    def check_if_all_quantity_is_withdrawn(self, customer):
        if customer.total > 0:
            return False
        if customer.total == 0:
            withdraws = self.env['amgl.metal_movement'].search([('customer', '=', customer.id), ('state', '!=', 'completed')])
            if withdraws:
                return False
            else:
                return True

    def calculate_current_inventory_values(self, customer, type):
        order_lines = self.env['amgl.order_line'].search([('customer_id', '=', customer.id)])
        all_withdrawn = self.check_if_all_quantity_is_withdrawn(customer)
        if all_withdrawn:
            return [0.00, 0.00, 0.00]

        filtered_order_lines = []
        for item in order_lines:
            if item.metal_movement_id:
                if item.metal_movement_id.state == 'completed':
                    filtered_order_lines.append(item)
            else:
                if not item.is_master_records:
                    filtered_order_lines.append(item)

        gold_price, palladium_price, platinum_price, silver_price = self.get_spot_price_from_amark()
        total_gold = total_silver = total_platinum = total_palladium = total = 0
        total_weight = gold_weight = silver_weight = platinum_weight = palladium_weight = 0
        for line in filtered_order_lines:
            for p in line.products:
                qty = line.total_received_quantity
                if p['type'] == 'Gold':
                    total_gold += qty
                    total += qty
                    gold_weight += self.calculate_weights(p, qty)
                    total_weight += self.calculate_weights(p, qty)
                if p['type'] == 'Silver':
                    total_silver += qty
                    total += qty
                    silver_weight += self.calculate_weights(p, qty)
                    total_weight += self.calculate_weights(p, qty)
                if p['type'] == 'Platinum':
                    total_platinum += qty
                    total += qty
                    platinum_weight += self.calculate_weights(p, qty)
                    total_weight += self.calculate_weights(p, qty)
                if p['type'] == 'Palladium':
                    total_palladium += qty
                    total += qty
                    palladium_weight += self.calculate_weights(p, qty)
                    total_weight += self.calculate_weights(p, qty)

        account_value = gold_weight * gold_price + silver_weight * silver_price + platinum_weight * platinum_price + palladium_weight * palladium_price

        if type == 'Gold':
            return [total_gold, round(gold_weight, 2), round(gold_weight * gold_price, 2)]
        if type == 'Silver':
            return [total_silver, round(silver_weight, 2), round(silver_weight * silver_price, 2)]
        if type == 'Platinum':
            return [total_platinum, round(platinum_weight, 2), round(platinum_weight * platinum_price, 2)]
        if type == 'Palladium':
            return [total_palladium, round(palladium_weight, 2), round(palladium_weight * palladium_price, 2)]
        if type == 'Total':
            return [total_gold + total_silver + total_platinum + total_palladium ,
                    round(gold_weight + silver_weight + platinum_weight + palladium_weight, 2),
                    round(account_value,2)]

    def filter_customers(self,docs):
        filtered_customers = []
        for customer in docs:
            order_lines = self.get_customer_master_order_lines(customer)
            if order_lines:
                filtered_customers.append(customer)
        return filtered_customers

    first_name = fields.Char('First Name', required=True)
    last_name = fields.Char('Last Name', required=True)
    account_number = fields.Char('Account Number', required=True)
    date_opened = fields.Date('Date Opened', required=True)
    account_type_restricted_group = fields.Boolean(default=False, compute="check_account_type_group")
    is_goldstar = fields.Boolean('Is GoldStar', default=False)
    is_admin = fields.Boolean(compute="check_user_group")
    is_custodian = fields.Boolean(compute="check_user_group")
    is_vault = fields.Boolean(compute="check_user_group")
    is_o2m = fields.Boolean(compute="check_user_group")
    is_account_closed = fields.Boolean(default=False, string="Account Closed")
    custodian_edit = fields.Boolean(default=False)
    allow_account_type_change = fields.Boolean(compute="check_account_type_change_access")
    full_name = fields.Char(string="Full Name", store=True)
    user_id = fields.Integer(default=
                             lambda self: self.env.user.id
                             if (self.env.user.partner_id.parent_id is False)
                             else self.env.user.partner_id.parent_id.id - 1)
    account_type = fields.Selection(selection=[('Commingled', 'Commingled'),
                                               ('Segregated', 'Segregated')], required=True)
    custodian_id = fields.Many2one('amgl.custodian', string="Custodian", required=True)
    number_of_orders = fields.Integer(string="Number Of Orders", compute="_get_number_of_orders")
    total_gold = fields.Integer(string='Total Gold', compute='_calculate_existing_inventory')
    total_silver = fields.Integer(string='Total Silver', compute='_calculate_existing_inventory')
    total_platinum = fields.Integer(string='Total Platinum', compute='_calculate_existing_inventory')
    total_palladium = fields.Integer(string='Total Palladium', compute='_calculate_existing_inventory')
    total = fields.Integer(string='Grand Total Pieces', compute='_calculate_existing_inventory')
    show_deposit = fields.Boolean(string='Show Deposit', default=True)
    # model changes
    customer_order_lines = fields.One2many('amgl.order_line', 'customer_id',
                                           compute="_compute_o2m_field")
    customer_order_lines2 = fields.One2many('amgl.order_line', 'customer_id', domain=[('is_master_records', '=', True),
                                                                                      ('total_received_quantity', '>',
                                                                                       0), ('is_active', '=', True)],
                                            string=' ')
    completed_mmr = fields.One2many('amgl.order_line', 'customer_id',
                                    compute="_get_completed_mmr_order_line")
    total_by_commodity = fields.Float(string="Grand Total Pieces", compute="_compute_total_by_commodity1")
    total_by_gold = fields.Float(string="Total Gold", compute="_compute_total_by_commodity1")
    total_by_silver = fields.Float(string="Total Silver", compute="_compute_total_by_commodity1")
    total_by_platinum = fields.Float(string="Total Platinum", compute="_compute_total_by_commodity1")
    total_by_palladium = fields.Float(string="Total Palladium", compute="_compute_total_by_commodity1")
    total_weight = fields.Float(string="Grand Total Weight", compute="_compute_total_by_commodity1")
    total_weight_store = fields.Float(string="Grand Total Weight")
    gold_weight = fields.Float(string="Total Gold", compute="_compute_total_by_commodity1")
    silver_weight = fields.Float(string="Total Silver", compute="_compute_total_by_commodity1")
    platinum_weight = fields.Float(string="Total Platinum", compute="_compute_total_by_commodity1")
    palladium_weight = fields.Float(string="Total Palladium", compute="_compute_total_by_commodity1")
    c_gold_weight = fields.Float(string="Total Gold", compute="_calculate_existing_inventory")
    c_silver_weight = fields.Float(string="Total Silver", compute="_calculate_existing_inventory")
    c_platinum_weight = fields.Float(string="Total Platinum", compute="_calculate_existing_inventory")
    c_palladium_weight = fields.Float(string="Total Palladium", compute="_calculate_existing_inventory")
    c_total_weight = fields.Float(string="Grand Total Weight", compute="_calculate_existing_inventory")
    gst_account_number = fields.Char(string="GoldStar Account#")
    nd_account_number = fields.Char(string="New Direction Account Number")
    c_total_gold_value = fields.Float(string="Total Gold Value", compute="_calculate_existing_inventory")
    c_total_silver_value = fields.Float(string="Total Silver Value", compute="_calculate_existing_inventory")
    c_total_platinum_value = fields.Float(string="Total Platinum Value", compute="_calculate_existing_inventory")
    c_total_palladium_value = fields.Float(string="Total Palladium Value", compute="_calculate_existing_inventory")
    c_total_value = fields.Float(string="Total Value", compute="_calculate_existing_inventory")
    p_total_gold_value = fields.Float(string="Total Gold Value", compute="_compute_total_by_commodity1")
    p_total_silver_value = fields.Float(string="Total Silver Value", compute="_compute_total_by_commodity1")
    p_total_platinum_value = fields.Float(string="Total Platinum Value", compute="_compute_total_by_commodity1")
    p_total_palladium_value = fields.Float(string="Total Palladium Value", compute="_compute_total_by_commodity1")
    p_total_value = fields.Float(string="Total Value", compute="_compute_total_by_commodity1")
    amark_customer_code = fields.Char(compute=generate_customer_code)
    customer_notes = fields.Text(string="Special Notes")
    total_account_value = fields.Float(compute=_calculate_existing_inventory)
    total_fees = fields.Float(compute=_calculate_existing_inventory)
    current_batch_total = fields.Float(string="Current Total : ", default=23232.54)
    state = fields.Selection(selection=[('Created', 'Created')], default='Created')
    customer_first_deposit_date = fields.Date(string="First Deposit Date", default='01/01/2000')
    custodian_edit_not_allowed = fields.Boolean(default=False, store=False)
    grace_period = fields.Selection(selection=[(1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 6), (7, 7), (8, 8), (9, 9)
        , (10, 10), (11, 11)])
    grace_period_selected = fields.Boolean(default=False, compute=get_customer_grace_period)
    user_role = fields.Char(compute=_get_current_user_role)
    is_grace_period_value_ever_given = fields.Boolean(default=False)
    is_customer_billed = fields.Boolean(default=False)
    # big_bar_order_lines = fields.One2many('amgl.order_line', 'customer_id', string=' ',
    #                                       domain=[('is_master_records', '=', True),
    #                                               ('total_received_quantity', '>',
    #                                                0), ('is_active', '=', True),
    #                                               ('weight_per_piece', '>', 900), ('weight_per_piece', '<', 1100)])
