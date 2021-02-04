# -*- coding: utf-8 -*-

import pysftp
import base64
import calendar
import datetime
import platform
import xlsxwriter
import csv
from dateutil import parser
from datetime import date, timedelta
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
import pytz


class Reports(models.Model):
    _name = 'amgl.reports'
    _description = 'Reports'

    gold_price = 0
    silver_price = 0
    platinum_price = 0
    palladium_price = 0

    @staticmethod
    def get_first_day(dt, d_years=0, d_months=0):
        y, m = dt.year + d_years, dt.month + d_months
        a, m = divmod(m - 1, 12)
        return date(y + a, m + 1, 1)

    @staticmethod
    def get_last_day(dt):
        return Reports.get_first_day(dt, 0, 1) + timedelta(-1)

    @staticmethod
    def go_back_month(dt):
        return dt - relativedelta(days=30)

    def generate_daily_details_transaction_report_csv(self, isEmailCalling):

        file_name = 'Equity - Daily Detail Transaction ' + datetime.datetime.now().strftime("%d-%B-%Y") + '.csv'
        base_url = self.env['ir.config_parameter'].get_param('amgl.live.url')

        if 'odev' in base_url or 'irastorage' in base_url:
            daily_transaction_csv_dir = '/opt/odoo/.local/share/Odoo/filestore/' + file_name
        else:
            daily_transaction_csv_dir = '/home/ahsan/AMARK/ExportFiles/' + file_name

        with open(daily_transaction_csv_dir, 'wb') as f:
            wr = csv.writer(f,quoting=csv.QUOTE_ALL)
            f.close()

        with open(daily_transaction_csv_dir, 'wb') as f:
            wr = csv.writer(f, quoting=csv.QUOTE_ALL)
            row = 'Date, Trans. Date, Type, Custodian, Acct#, Name, Class, Qty, Product, Product Code, Total Ounces'
            f.write(row)
            f.write('\n')
            cust_code = 'ETI'
            yesterday_date = datetime.datetime.today() - datetime.timedelta(1)

            if isEmailCalling:
                order_lines = self.env['amgl.order_line'].search(
                    [('is_master_records', '=', False), ('is_active', '=', True), ('custodian_code', '=', cust_code),
                     ('date_received', '=', str(yesterday_date))],
                    order='transaction_detail_sort_date asc, customer_id')
            else:
                order_lines = self.env['amgl.order_line'].search(
                    [('is_master_records', '=', False), ('is_active', '=', True), ('custodian_code', '=', cust_code)],
                    order='transaction_detail_sort_date asc, customer_id')

            filtered_order_lines = []
            for item in order_lines:
                item_month = datetime.datetime.strptime(item.transaction_detail_sort_date, '%Y-%m-%d').month
                item_year = datetime.datetime.strptime(item.transaction_detail_sort_date, '%Y-%m-%d').year
                current_month = datetime.datetime.today().month
                current_year = datetime.datetime.today().year
                if item_year == current_year:
                    if item_month == current_month:
                        filtered_order_lines.append(item)

            for customer_order in filtered_order_lines:
                cs = self.env['amgl.customer'].search([('id', '=', customer_order.customer_id.id)])
                init_date = datetime.datetime.strptime(cs.create_date, '%Y-%m-%d %H:%M:%S').strftime(
                    '%m/%d/%y')
                row = customer_order.transaction_detail_sort_date + ','
                row += customer_order.create_date + ','
                row += 'D,' if customer_order.metal_movement_id.id is False else 'W,'
                row += 'ETI' + ','
                row += cs.account_number + ','
                row += cs.full_name.replace(',','') + ','
                row += 'Comm,' if cs.account_type == 'Commingled' else 'Seg,'
                row += str(customer_order.total_received_quantity) + ','
                row += customer_order.products.goldstar_name.replace(',','') + ','
                row += customer_order.products.product_code.replace(',','') + ','
                row += str(customer_order.temp_received_weight)
                f.write(row)
                f.write('\n')
            f.close()
            attachment = self.add_csv_file_in_attachment(daily_transaction_csv_dir, file_name)
        return attachment, file_name

    def calculate_total_weight_after_including_completed_withdrawal(self, order):
        master_product_quantity = order.temp_received_weight
        order_lines = self.env['amgl.order_line'].search(
            [('products', '=', order.products.id), ('is_master_records', '=', False), ('customer_id', '=', order.customer_id.id)])
        if order_lines:
            for item in order_lines:
                if item.metal_movement_id and item.metal_movement_id.state != 'completed' and item.metal_movement_id.mmr_number:
                    master_product_quantity += (-item.temp_received_weight)
        return master_product_quantity

    def generate_custodian_inventory_by_customer(self):
        all_customer_total_gold = 0.0
        all_customer_total_silver = 0.0
        all_customer_total_platinum = 0.0
        all_customer_total_palladium = 0.0

        file_name = 'Custodian Inventory By Customer ' + datetime.datetime.now().strftime("%d-%B-%Y") + '.csv'
        base_url = self.env['ir.config_parameter'].get_param('amgl.live.url')

        if 'odev' in base_url or 'irastorage' in base_url:
            daily_transaction_csv_dir = '/opt/odoo/.local/share/Odoo/filestore/' + file_name
        else:
            daily_transaction_csv_dir = '/home/ahsan/AMARK/ExportFiles/' + file_name

        customers = self.env['amgl.customer'].search(
            [('custodian_id', '=', self.custodian.id), ('is_account_closed', '=', False)],
            order='last_name asc')
        with open(daily_transaction_csv_dir, 'wb') as f:
            wr = csv.writer(f, quoting=csv.QUOTE_ALL)
            f.close()

        with open(daily_transaction_csv_dir, 'wb') as f:
            wr = csv.writer(f, quoting=csv.QUOTE_ALL)

            for customer in customers:
                total_gold = 0.0
                total_silver = 0.0
                total_platinum = 0.0
                total_palladium = 0.0
                product_total_gold = 0.0
                product_total_silver = 0.0
                product_total_platinum = 0.0
                product_total_palladium = 0.0
                customer_name = customer.account_number if customer.gst_account_number is False else customer.gst_account_number
                row = 'Name : '+customer.full_name.upper() + ', Account# : ' + customer_name + ', Account Type : ' + customer.account_type
                f.write(row)
                f.write('\n')
                f.write('\n')
                customer_orders = self.env['amgl.order_line'].search(['&', ('is_master_records', '=', False),
                                                                      ('is_active', '=', True),
                                                                      ('customer_id', '=', customer.id)],
                                                                     order='transaction_detail_sort_date asc, customer_id')
                row = 'Products, Product Code, Gold Oz., Silver Oz., Platinum Oz., Palladium Oz.'
                f.write(row)
                f.write('\n')
                for customer_order in customer_orders:
                    if customer_order.products.type == 'Gold':
                        product_total_gold = self.calculate_total_weight_after_including_completed_withdrawal(customer_order)
                        total_gold += product_total_gold
                        all_customer_total_gold += total_gold
                    if customer_order.products.type == 'Silver':
                        product_total_silver += self.calculate_total_weight_after_including_completed_withdrawal(customer_order)
                        all_customer_total_silver += total_silver
                        total_silver += product_total_silver
                    if customer_order.products.type == 'Platinum':
                        product_total_platinum += self.calculate_total_weight_after_including_completed_withdrawal(customer_order)
                        all_customer_total_platinum += total_platinum
                        total_platinum += product_total_platinum
                    if customer_order.products.type == 'Palladium':
                        product_total_palladium += self.calculate_total_weight_after_including_completed_withdrawal(customer_order)
                        all_customer_total_palladium += total_palladium
                        total_palladium += product_total_palladium

                    if customer_order.is_master_records is False:
                        row = customer_order.products.name.replace(',', '') + ','
                        row += customer_order.products.product_code + ','
                        row += str(product_total_gold) + ',' if customer_order.products.type == 'Gold' else '0.0 ,'
                        row += str(product_total_silver) + ',' if customer_order.products.type == 'Silver' else '0.0 ,'
                        row += str(product_total_platinum) + ',' if customer_order.products.type == 'Platinum' else '0.0 ,'
                        row += str(product_total_palladium) + ',' if customer_order.products.type == 'Palladium' else '0.0'
                        f.write(row)
                        f.write('\n')

                f.write('\n')
                row = 'GRAND TOTAL,'
                row += ','
                row += str(total_gold) + ','
                row += str(total_silver) + ','
                row += str(total_platinum) + ','
                row += str(total_palladium) + ','
                f.write(row)
                f.write('\n')
                f.write('\n')
            f.write('\n')
            f.write('\n')
            f.close()
            attachment = self.add_csv_file_in_attachment(daily_transaction_csv_dir, file_name)
        return attachment, file_name

    def get_products(self, type):
        products = self.env['amgl.products'].search([('type', '=', type)])
        product_names = []
        for item in products:
            product_names.append(item.goldstar_name)

        product_names = list(dict.fromkeys(product_names))
        product_names = sorted(product_names)
        return product_names

    def get_products_total_quantity(self, product, custodian, account_type):
        _product = self.env['amgl.products'].search([('goldstar_name', '=', product)], limit=1)
        _custodian = self.env['amgl.custodian'].search([('name', '=', custodian)])
        if '' == account_type:
            customers = self.env['amgl.customer'].search(
                [('is_account_closed', '=', False), ('custodian_id', '=', _custodian.id)]).ids
        else:
            customers = self.env['amgl.customer'].search(
                [('is_account_closed', '=', False), ('custodian_id', '=', _custodian.id),
                 ('account_type', '=', account_type)]).ids

        order_lines = self.env['amgl.order_line'].search(
            [('products', '=', _product.id), ('is_master_records', '=', True), ('customer_id', 'in', customers)])
        total_quantity = 0
        for item in order_lines:
            total_quantity += self.get_total_quantity_after_including_completed_withdrawal(item)

        return total_quantity

    def fetch_reports(self):
        result = ''
        custodians = self.env['amgl.custodian'].search([])
        new_direction_id = 0
        gold_star_id = 0
        provident_trust_id = 0
        equity_id = 0
        for custodian in custodians:
            if 'New Direction' in custodian.name:
                new_direction_id = custodian.id
            if 'Gold' in custodian.name:
                gold_star_id = custodian.id
            if 'Provident' in custodian.name:
                provident_trust_id = custodian.id
            if 'Equity' in custodian.name:
                equity_id = custodian.id

        self.validate_month_and_year_selection()
        if self.month and self.year:
            month = int(self.month)
            year = int(self.year)
            start_date = datetime.datetime(int(year), int(month), 1)
            if int(self.month) < 12:
                end_date = datetime.datetime(int(year), int(month) + 1, 1) - relativedelta(days=1)
            else:
                end_date = datetime.datetime(int(year), int(month), 31)
        if 'physical' in self.report_types:
            customers = self.env['amgl.customer'].search([('is_account_closed', '=', False)]).ids
            report_name = 'amgl.physical_inventory_report_template'
            data_object = {
                'ids': customers,
                'model': 'amgl.customer',
                'form': customers
            }
            selected_date = datetime.datetime.now()
            context = dict(self.env.context,
                           selected_date=str(calendar.month_name[selected_date.month]) + ", " + str(selected_date.year))
            return {
                'type': 'ir.actions.report.xml',
                'report_name': report_name,
                'datas': data_object,
                'context': context
            }
        if 'custodian_inventory_by_customer' in self.report_types:
            customers = []
            if 'csv' in self.report_format:
                attachment, file_name = self.generate_custodian_inventory_by_customer()
                base_url = self.env['ir.config_parameter'].get_param('amgl.live.url')
                return {
                    'type': 'ir.actions.act_url',
                    'url': base_url + '/web/content/%s/%s' % (attachment.id, file_name.replace('/excel/', '')),
                    'target': 'self'
                }

            if 'custodian_inventory_by_customer_segregated' == self.report_types:
                customers = self.env['amgl.customer'].search(
                    [('custodian_id', '=', self.custodian.id), ('account_type', '=', 'Segregated'), ('is_account_closed', '=', False)],
                    order='last_name asc').ids
            if 'custodian_inventory_by_customer_commingled' == self.report_types:
                customers = self.env['amgl.customer'].search(
                    [('custodian_id', '=', self.custodian.id), ('account_type', '=', 'Commingled'), ('is_account_closed', '=', False)],
                    order='last_name asc').ids
            if 'custodian_inventory_by_customer' == self.report_types:
                customers = self.env['amgl.customer'].search([('custodian_id', '=', self.custodian.id), ('is_account_closed', '=', False)],
                                                             order='last_name asc').ids

            report_name = 'amgl.custodian_inventory_by_customer_report_template'
            data_object = {
                'ids': customers,
                'model': 'amgl.customer',
                'form': customers
            }
            selected_date = datetime.datetime.now()
            context = dict(self.env.context,
                           selected_date=str(calendar.month_name[selected_date.month]) + ", " + str(selected_date.year))
            return {
                'type': 'ir.actions.report.xml',
                'report_name': report_name,
                'datas': data_object,
                'context': context
            }
        if 'custodian_inventory_by_product' in self.report_types:
            customers = []
            if 'custodian_inventory_by_product_segregated' == self.report_types:
                if 'excel' in self.report_format:
                    attachment, file_name = self.create_custodian_inventory_for_product('segregated')
                    base_url = self.env['ir.config_parameter'].get_param('amgl.live.url')
                    return {
                        'type': 'ir.actions.act_url',
                        'url': base_url + '/web/content/%s/%s' % (attachment.id, file_name.replace('/excel/', '')),
                        'target': 'self'
                    }
                customers = self.env['amgl.customer'].search(
                    [('custodian_id', '=', self.custodian.id), ('account_type', '=', 'Segregated'),
                     ('is_account_closed', '=', False)],
                    order='last_name asc').ids
            if 'custodian_inventory_by_product_commingled' == self.report_types:
                if 'excel' in self.report_format:
                    attachment, file_name = self.create_custodian_inventory_for_product('commingled')
                    base_url = self.env['ir.config_parameter'].get_param('amgl.live.url')
                    return {
                        'type': 'ir.actions.act_url',
                        'url': base_url + '/web/content/%s/%s' % (attachment.id, file_name.replace('/excel/', '')),
                        'target': 'self'
                    }
                customers = self.env['amgl.customer'].search(
                    [('custodian_id', '=', self.custodian.id), ('account_type', '=', 'Commingled'),
                     ('is_account_closed', '=', False)],
                    order='last_name asc').ids
            if 'custodian_inventory_by_product' == self.report_types:
                if 'excel' in self.report_format:
                    attachment, file_name = self.create_custodian_inventory_for_product('full')
                    base_url = self.env['ir.config_parameter'].get_param('amgl.live.url')
                    return {
                        'type': 'ir.actions.act_url',
                        'url': base_url + '/web/content/%s/%s' % (attachment.id, file_name.replace('/excel/', '')),
                        'target': 'self'
                    }
                customers = self.env['amgl.customer'].search([('custodian_id', '=', self.custodian.id),
                                                              ('is_account_closed', '=', False)],
                                                             order='last_name asc').ids

            report_name = 'amgl.custodian_inventory_by_product_report_template'
            data_object = {
                'ids': customers,
                'model': 'amgl.customer',
                'form': customers
            }
            selected_date = datetime.datetime.now()
            context = dict(self.env.context,
                           selected_date=str(calendar.month_name[selected_date.month]) + ", " + str(selected_date.year))
            return {
                'type': 'ir.actions.report.xml',
                'report_name': report_name,
                'datas': data_object,
                'context': context
            }
        if 'detail_transaction_report' == self.report_types:
            order_lines = self.env['amgl.order_line'].search(
                [('is_master_records', '=', False), ('is_active', '=', True)],
                order='transaction_detail_sort_date asc, customer_id')
            filtered_order_line_ids = []
            for item in order_lines:
                item_month = datetime.datetime.strptime(item.transaction_detail_sort_date, '%Y-%m-%d').month
                item_year = datetime.datetime.strptime(item.transaction_detail_sort_date, '%Y-%m-%d').year
                if item_year == year:
                    if item_month == month:
                        filtered_order_line_ids.append(item.id)

            report_name = 'amgl.detailed_transaction_report_template'
            data_object = {
                'ids': filtered_order_line_ids,
                'model': 'amgl.order_line',
                'form': filtered_order_line_ids
            }
            selected_date = datetime.datetime(int(self.year), int(self.month), 1)
            context = dict(self.env.context,
                           selected_date=str(calendar.month_name[selected_date.month]) + ", " + str(selected_date.year))
            return {
                'type': 'ir.actions.report.xml',
                'report_name': report_name,
                'datas': data_object,
                'context': context
            }
        if 'daily_detail_transaction_report' == self.report_types:
            if 'excel' in self.report_format:
                self.report_validation_message = 'Excel format for this report is not available.'
            elif 'csv' in self.report_format:
                attachment, file_name = self.generate_daily_details_transaction_report_csv(False)
                base_url = self.env['ir.config_parameter'].get_param('amgl.live.url')
                return {
                    'type': 'ir.actions.act_url',
                    'url': base_url + '/web/content/%s/%s' % (attachment.id, file_name.replace('/excel/', '')),
                    'target': 'current'
                }
            else:
                custodian = self.env['amgl.custodian'].search([('custodian_code', '=', 'ETI')])
                filtered_order_line_ids = []
                customers = self.env['amgl.customer'].search([('is_account_closed', '=', False),
                                                              ('custodian_id', '=', custodian.id)])

                for customer in customers:
                    customer_orders = self.env['amgl.order_line'].search(['&', ('is_master_records', '=', False),
                                                                  ('is_active', '=', True),
                                                                  ('customer_id', '=', customer.id)],
                                                                 order='transaction_detail_sort_date asc, customer_id')

                    for item in customer_orders:
                        item_month = datetime.datetime.strptime(item.transaction_detail_sort_date, '%Y-%m-%d').month
                        item_year = datetime.datetime.strptime(item.transaction_detail_sort_date, '%Y-%m-%d').year
                        if item_year == year:
                            if item_month == month:
                                filtered_order_line_ids.append(item.id)

                report_name = 'amgl.daily_detailed_transaction_report_template'
                data_object = {
                    'ids': filtered_order_line_ids,
                    'model': 'amgl.order_line',
                    'form': filtered_order_line_ids
                }
                selected_date = datetime.datetime(int(self.year), int(self.month), 1)
                context = dict(self.env.context,
                               selected_date=str(calendar.month_name[selected_date.month]) + ", " + str(selected_date.year))
                return {
                    'type': 'ir.actions.report.xml',
                    'report_name': report_name,
                    'datas': data_object,
                    'context': context
                }

        if 'customer_position_listing' in self.report_types:
            customers = self.env['amgl.customer'].search([('custodian_id', '=', self.custodian.id), ('is_account_closed', '=', False)],
                                                         order='last_name asc').ids
            report_name = self.fetch_report_name()
            data_object = {
                'ids': customers,
                'model': 'amgl.customer',
                'form': customers
            }
            selected_date = datetime.datetime.now()
            context = dict(self.env.context,
                           selected_date=str(calendar.month_name[selected_date.month]) + ", " + str(selected_date.year))
            return {
                'type': 'ir.actions.report.xml',
                'report_name': report_name,
                'datas': data_object,
                'context': context
            }
        if 'customer_history_by_product' in self.report_types:
            customers = self.env['amgl.customer'].search([('custodian_id', '=', self.custodian.id), ('is_account_closed', '=', False)],
                                                         order='last_name asc').ids
            report_name = self.fetch_report_name()
            data_object = {
                'ids': customers,
                'model': 'amgl.customer',
                'form': customers
            }
            selected_date = datetime.datetime.now()
            context = dict(self.env.context,
                           selected_date=str(calendar.month_name[selected_date.month]) + ", " + str(selected_date.year))
            return {
                'type': 'ir.actions.report.xml',
                'report_name': report_name,
                'datas': data_object,
                'context': context
            }
        if 'combined_holding_statement' == self.report_types:
            return self.generate_combined_holding_statement_report()
        if 'combined_holding_statement_by_customer' == self.report_types:
            return self.generate_combined_holding_by_customer_report()
        if 'customer_fair_holdings' == self.report_types:
            return self.generate_customer_fair_holdings_report()

        base_url = self.env['ir.config_parameter'].get_param('amgl.live.url')
        attachment_id = 0
        file_name = ''
        if 'New Direction' in self.custodian.name:
            if 'new_accounts' in self.report_types or 'existing' in self.report_types:
                self.is_report_format_selected()
            if 'new_accounts' in self.report_types:
                result,attachment_id,file_name = self.generate_new_accounts_invoice_for_new_direction(start_date, end_date, new_direction_id)
            if 'existing' in self.report_types:
                result,attachment_id,file_name = self.generate_existing_accounts_invoice_for_new_direction(start_date, end_date,
                                                                                   new_direction_id)
        if 'GoldStar' in self.custodian.name:
            if 'new_accounts' in self.report_types or 'existing' in self.report_types:
                self.is_report_format_selected()
            if 'new_accounts' in self.report_types:
                result,attachment_id,file_name  = self.generate_new_accounts_invoice_for_gold_star(start_date, end_date, gold_star_id)
            if 'existing' in self.report_types:
                result,attachment_id,file_name  = self.generate_existing_accounts_invoice_for_gold_star(start_date, end_date, gold_star_id)
        if 'Provident' in self.custodian.name:
            if 'new_accounts' in self.report_types or 'existing' in self.report_types:
                self.is_report_format_selected()
            if 'new_accounts' in self.report_types:
                result,attachment_id,file_name = self.generate_new_accounts_invoice_for_provident_trust(start_date, end_date, provident_trust_id)
            if 'existing' in self.report_types:
                result,attachment_id,file_name = self.generate_existing_accounts_invoice_for_provident_trust(start_date, end_date, provident_trust_id)
        if 'Equity' in str(self.custodian.name):
            if 'new_accounts' in self.report_types or 'existing' in self.report_types:
                self.is_report_format_selected()
            if 'new_accounts' in self.report_types:
                result,attachment_id,file_name = self.generate_new_accounts_invoice_for_new_direction(start_date, end_date, equity_id)
            if 'existing' in self.report_types:
                result,attachment_id,file_name = self.generate_existing_accounts_invoice_for_new_direction(start_date, end_date,
                                                                                                           equity_id)
        if attachment_id > 0: #For Excel Versions of Billing Invoices
            return {
                'type': 'ir.actions.act_url',
                'url': base_url + '/web/content/%s/%s' % (attachment_id, file_name.replace('/excel/', '')),
                'target': 'self'
            }
        else:
            return result

    def is_report_format_selected(self):
        if not self.report_format:
            raise ValidationError('Report format must be selected for Storage Invoice.')

    def validate_month_and_year_selection(self):
        if self.report_types and (
                'new_accounts' in self.report_types or 'existing' in self.report_types or 'detail_transaction_report' in self.report_types or 'custodian_transaction_report' in self.report_types):
            if not self.month and not self.year:
                raise ValidationError('Select month and year to download the report.')
            if not self.month:
                raise ValidationError('Select month to download the report.')
            if not self.year:
                raise ValidationError('Select year to download the report.')

    @api.multi
    def fetch_transaction_invoice(self):
        self.validate_month_and_year_selection()
        start_date = datetime.datetime(int(self.year), int(self.month), 1)
        if int(self.month) < 12:
            end_date = datetime.datetime(int(self.year), int(self.month) + 1, 1) - relativedelta(days=1)
        else:
            end_date = datetime.datetime(int(self.year), int(self.month), 31)

        if not self.report_format:
            raise ValidationError('Report format must be selected for Transaction Invoice.')
        if 'excel' in self.report_format:
            attachment_id, file_name = self.create_excel_file(start_date, end_date)
            base_url = self.env['ir.config_parameter'].get_param('amgl.live.url')
            return {
                'type': 'ir.actions.act_url',
                'url': base_url + '/web/content/%s/%s' % (attachment_id, file_name.replace('/excel/', '')),
                'target': 'self'
            }
        if 'pdf' in self.report_format:
            report_name = str(calendar.month_name[datetime.datetime.now().month]) + ' ' + str(
                datetime.datetime.now().year) + ' Transaction Invoice.pdf'

            filtered_transactions = self.env['amgl.fees'].search([])
            customers = self.env['amgl.customer'].search([('is_account_closed', '=', False), ('custodian_id', '=', self.custodian.id)])
            customer_transactions_ids = []
            for customer in customers:
                # if customer.grace_period:
                # customer_order_lines = self.env['amgl.order_line'].search(
                #     ['&', ('customer_id', '=', customer.id), ('is_master_records', '=', False)],
                #     order='date_received asc')
                # if customer_order_lines:
                #     first_deposit_date = customer_order_lines[0].date_received
                #     temp_end_of_period = parser.parse(first_deposit_date) + relativedelta(
                #         months=customer.grace_period)
                #     end_of_period = parser.parse(str(temp_end_of_period)).date()
                #     today_date = datetime.datetime.now().date()
                #     if today_date <= end_of_period:
                #         continue

                customer_transactions = []
                for item in filtered_transactions:
                    if item.customer_id.id == customer.id:
                        customer_transactions.append(item)

                for transaction in customer_transactions:
                    # if transaction.order_line_id and transaction.inbound_fees > 0.0:
                    #     order_line = self.env['amgl.order_line'].search([('id', '=', transaction.order_line_id.id)])
                    #     date_received = datetime.datetime.strptime(order_line.date_received, '%Y-%m-%d')
                    #     if date_received >= start_date and date_received <= end_date:
                    #         customer_transactions_ids.append(transaction.id)
                    if transaction.metal_movement_id and transaction.total_fees > 0.0:
                        metal_movement = self.env['amgl.metal_movement'].search(
                            [('id', '=', transaction.metal_movement_id.id)])
                        date_create = datetime.datetime.strptime(metal_movement.date_create, '%Y-%m-%d')
                        if date_create >= start_date and date_create <= end_date:
                            customer_transactions_ids.append(transaction.id)

            data_object = {
                'ids': customer_transactions_ids,
                'model': 'amgl.fees',
                'form': customer_transactions_ids
            }
            return {
                'type': 'ir.actions.report.xml',
                'report_name': 'amgl.transaction_invoice_report_template',
                'datas': data_object,
            }

    def generate_existing_accounts_invoice_for_gold_star(self, start_date, end_date, gold_star_id):
        result = ''
        file_name = ''
        attachment_id = 0
        if 'commingled' in self.report_types:
            existing_customers = self.get_existing_commingled_customer_for_storage_invoice(start_date, end_date,
                                                                                           gold_star_id)
            if 'excel' in self.report_format:
                attachment_id, file_name = self.create_excel_file_for_storage_invoice(start_date, end_date,existing_customers, 'commingled',
                                                                                      'existing', 'GoldStar')
            else:
                result = self.gold_star_accounts_storage_invoice(existing_customers, self.report_types, start_date)
        elif 'segregated' in self.report_types:
            existing_customers = self.get_existing_segregated_customer_for_storage_invoice(start_date, end_date,
                                                                                           gold_star_id)
            if 'excel' in self.report_format:
                attachment_id, file_name = self.create_excel_file_for_storage_invoice(start_date, end_date,existing_customers, 'segregated',
                                                                                      'existing', 'GoldStar')
            else:
                result = self.gold_star_accounts_storage_invoice(existing_customers, self.report_types, start_date)
        return result,attachment_id, file_name

    def get_existing_segregated_customer_for_storage_invoice(self, start_date, end_date, gold_star_id):
        customers = self.env['amgl.customer'].search(
            ['&', ('account_type', '=', 'Segregated'),('is_customer_billed', '=', True), ('is_account_closed', '=', False), ('custodian_id', '=', gold_star_id)],
            order='account_type desc')
        filtered_customer_ids = []
        for customer in customers:
            first_order = self.env['amgl.order_line'].search(
                [('customer_id', '=', customer.id), ('metal_movement_id', '=', False),
                 ('is_master_records', '=', False)], order='date_received asc',
                limit=1)
            if first_order:
                billing_month = start_date.month
                billing_year = end_date.year
                first_order_month = datetime.datetime.strptime(first_order.date_received, '%Y-%m-%d').month
                year_difference = billing_year - datetime.datetime.strptime(first_order.date_received,
                                                                            '%Y-%m-%d').year
                first_order_year = (datetime.datetime.strptime(first_order.date_received,
                                                               '%Y-%m-%d') + relativedelta(years=year_difference)).year

                if first_order_month == billing_month and first_order_year == billing_year and year_difference > 0:
                    filtered_customer_ids.append(customer.id)
        existing_customers = self.env['amgl.customer'].search([('id', 'in', filtered_customer_ids)]).ids
        return existing_customers

    def get_existing_commingled_customer_for_storage_invoice(self, start_date, end_date, gold_star_id):
        customers = self.env['amgl.customer'].search(
            ['&', ('account_type', '=', 'Commingled'),('is_customer_billed', '=', True), ('is_account_closed', '=', False), ('custodian_id', '=', gold_star_id)],
            order='account_type desc')
        filtered_customer_ids = []
        for customer in customers:
            first_order = self.env['amgl.order_line'].search(
                [('customer_id', '=', customer.id), ('metal_movement_id', '=', False),
                 ('is_master_records', '=', False)], order='date_received asc',
                limit=1)
            if first_order:
                billing_month = start_date.month
                billing_year = end_date.year
                first_order_month = datetime.datetime.strptime(first_order.date_received, '%Y-%m-%d').month
                year_difference = billing_year - datetime.datetime.strptime(first_order.date_received,
                                                                            '%Y-%m-%d').year
                first_order_year = (datetime.datetime.strptime(first_order.date_received,
                                                               '%Y-%m-%d') + relativedelta(years=year_difference)).year

                if first_order_month == billing_month and first_order_year == billing_year and year_difference > 0:
                    filtered_customer_ids.append(customer.id)
        existing_customers = self.env['amgl.customer'].search([('id', 'in', filtered_customer_ids)]).ids
        return existing_customers

    def generate_new_accounts_invoice_for_gold_star(self, start_date, end_date, gold_star_id):
        result = ''
        file_name = ''
        attachment_id = 0
        if 'commingled' in self.report_types:
            new_customers = self.get_new_commingled_customer_for_storage_invoice(start_date, end_date, gold_star_id)
            if 'excel' in self.report_format:
                attachment_id, file_name = self.create_excel_file_for_storage_invoice(start_date, end_date,new_customers, 'commingled',
                                                                                      'new', 'GoldStar')
            else:
                result = self.gold_star_accounts_storage_invoice(new_customers, self.report_types, start_date)
        elif 'segregated' in self.report_types:
            new_customers = self.get_new_segregated_customer_for_storage_invoice(start_date, end_date, gold_star_id)
            if 'excel' in self.report_format:
                attachment_id, file_name = self.create_excel_file_for_storage_invoice(start_date, end_date,new_customers, 'segregated',
                                                                                      'new', 'GoldStar')
            else:
                result = self.gold_star_accounts_storage_invoice(new_customers, self.report_types, start_date)
        if len(new_customers) > 0 and self.bill_customers:
            self.update_customers(new_customers)
        return result,attachment_id, file_name

    def get_new_segregated_customer_for_storage_invoice(self, start_date, end_date, gold_star_id):
        customers = self.env['amgl.customer'].search(
            ['&', ('account_type', '=', 'Segregated'),('is_account_closed', '=', False), ('custodian_id', '=', gold_star_id),
             ('customer_first_deposit_date', '>=', start_date), ('customer_first_deposit_date', '<=', end_date),
             ('is_customer_billed', '=', False),('customer_first_deposit_date', '!=', '2000-01-01')],
            order='account_type desc')
        filtered_customer_ids = []
        for customer in customers:
            # if customer.grace_period:
            #     customer_order_lines = self.env['amgl.order_line'].search(
            #         ['&', ('customer_id', '=', customer.id), ('is_master_records', '=', False)],
            #         order='date_received asc')
            #     if customer_order_lines:
            #         first_deposit_date = customer_order_lines[0].date_received
            #         temp_end_of_period = parser.parse(first_deposit_date) + relativedelta(
            #             months=customer.grace_period)
            #         end_of_period = parser.parse(str(temp_end_of_period)).date()
            #         today_date = datetime.datetime.now().date()
            #         if today_date <= end_of_period:
            #             continue

            # customer_orders = self.env['amgl.order_line'].search(
            #     ['&', ('customer_id', '=', customer.id), ('metal_movement_id', '=', False),
            #      ('is_master_records', '=', False)], order='date_received asc')
            # customer_allowed_on_report = False
            # for order in customer_orders:
            #     date_received = datetime.datetime.strptime(order.date_for_customer_metal_activitiy, '%Y-%m-%d')
            #     if date_received >= start_date and date_received <= end_date:
            #         customer_allowed_on_report = True
            #     else:
            #         customer_allowed_on_report = False
            #         break;
            # if customer_allowed_on_report:
            filtered_customer_ids.append(customer.id)
        if self.bill_customers and len(filtered_customer_ids) == 0:
            customers = self.env['amgl.customer'].search(
                ['&', ('account_type', '=', 'Segregated'), ('is_account_closed', '=', False),
                 ('custodian_id', '=', gold_star_id),
                 ('customer_first_deposit_date', '>=', start_date), ('customer_first_deposit_date', '<=', end_date),
                 ('is_customer_billed', '=', True), ('customer_first_deposit_date', '!=', '2000-01-01')],
                order='account_type desc')
            if len(customers) > 0:
                raise ValidationError("Inovice for the selection has already been submitted!")
        new_customers = self.env['amgl.customer'].search([('id', 'in', filtered_customer_ids)]).ids
        return new_customers

    def get_new_commingled_customer_for_storage_invoice(self, start_date, end_date, gold_star_id):
        customers = self.env['amgl.customer'].search(
            ['&', ('account_type', '=', 'Commingled'), ('is_account_closed', '=', False), ('custodian_id', '=', gold_star_id),
             ('customer_first_deposit_date', '>=', start_date), ('customer_first_deposit_date', '<=', end_date),
             ('is_customer_billed', '=', False),('customer_first_deposit_date', '!=', '2000-01-01')],
            order='account_type desc')
        filtered_customer_ids = []
        for customer in customers:
            # if customer.grace_period:
            #     customer_order_lines = self.env['amgl.order_line'].search(
            #         ['&', ('customer_id', '=', customer.id), ('is_master_records', '=', False)],
            #         order='date_received asc')
            #     if customer_order_lines:
            #         first_deposit_date = customer_order_lines[0].date_received
            #         temp_end_of_period = parser.parse(first_deposit_date) + relativedelta(
            #             months=customer.grace_period)
            #         end_of_period = parser.parse(str(temp_end_of_period)).date()
            #         today_date = datetime.datetime.now().date()
            #         if today_date <= end_of_period:
            #             continue

            # customer_orders = self.env['amgl.order_line'].search(
            #     ['&', ('customer_id', '=', customer.id), ('metal_movement_id', '=', False),
            #      ('is_master_records', '=', False)], order='date_received asc')
            # customer_allowed_on_report = False
            # for order in customer_orders:
            #     date_received = datetime.datetime.strptime(order.date_for_customer_metal_activitiy, '%Y-%m-%d')
            #     if date_received >= start_date and date_received <= end_date:
            #         customer_allowed_on_report = True
            #     else:
            #         customer_allowed_on_report = False
            #         break;
            # if customer_allowed_on_report:
            filtered_customer_ids.append(customer.id)
        if self.bill_customers and len(filtered_customer_ids) == 0:
            customers = self.env['amgl.customer'].search(
                ['&', ('account_type', '=', 'Commingled'), ('is_account_closed', '=', False),
                 ('custodian_id', '=', gold_star_id),
                 ('customer_first_deposit_date', '>=', start_date), ('customer_first_deposit_date', '<=', end_date),
                 ('is_customer_billed', '=', True), ('customer_first_deposit_date', '!=', '2000-01-01')],
                order='account_type desc')
            if len(customers) > 0:
                raise ValidationError("Inovice for the selection has already been submitted!")
        new_customers = self.env['amgl.customer'].search([('id', 'in', filtered_customer_ids)]).ids
        return new_customers

    def generate_existing_accounts_invoice_for_new_direction(self, start_date, end_date, new_direction_id):
        result = ''
        file_name = ''
        attachment_id = 0
        if 'commingled' in self.report_types:
            existing_customers = self.get_existing_commingled_customer_for_storage_invoice_new_direction(start_date,
                                                                                                         end_date,
                                                                                                     new_direction_id)
            if 'excel' in self.report_format:
                attachment_id, file_name = self.create_excel_file_for_storage_invoice(start_date,end_date,
                                                          existing_customers, 'commingled', 'existing',
                                                                                      str(self.custodian.name))
            else:
                result = self.new_direction_accounts_storage_invoice(existing_customers, self.report_types, start_date)
        elif 'segregated' in self.report_types:
            existing_customers = self.get_existing_segregated_customer_for_storage_invoice_new_direction(start_date,
                                                                                                         end_date,
                                                                                                     new_direction_id)
            if 'excel' in self.report_format:
                attachment_id, file_name = self.create_excel_file_for_storage_invoice(start_date,end_date,
                                                                    existing_customers, 'segregated', 'existing',
                                                                                      str(self.custodian.name))
            else:
                result = self.new_direction_accounts_storage_invoice(existing_customers, self.report_types, start_date)

        return result,attachment_id, file_name

    def get_existing_segregated_customer_for_storage_invoice_new_direction(self, start_date, end_date,
                                                                           new_direction_id):
        customers = self.env['amgl.customer'].search(
            ['&', ('account_type', '=', 'Segregated'),('is_customer_billed', '=', True),('is_account_closed', '=', False), ('custodian_id', '=', new_direction_id)],
            order='account_type desc')
        filtered_customer_ids = []
        for customer in customers:
            first_order = self.env['amgl.order_line'].search(
                [('customer_id', '=', customer.id), ('metal_movement_id', '=', False),
                 ('is_master_records', '=', False)], order='date_received asc',
                limit=1)
            if first_order:
                billing_month = start_date.month
                billing_year = end_date.year
                first_order_month = datetime.datetime.strptime(first_order.date_received, '%Y-%m-%d').month
                year_difference = billing_year - datetime.datetime.strptime(first_order.date_received,
                                                                            '%Y-%m-%d').year
                first_order_year = (datetime.datetime.strptime(first_order.date_received,
                                                               '%Y-%m-%d') + relativedelta(years=year_difference)).year

                if first_order_month == billing_month and first_order_year == billing_year and year_difference > 0:
                    filtered_customer_ids.append(customer.id)
        existing_customers = self.env['amgl.customer'].search([('id', 'in', filtered_customer_ids)]).ids
        return existing_customers

    def get_existing_commingled_customer_for_storage_invoice_new_direction(self, start_date, end_date,
                                                                           new_direction_id):
        customers = self.env['amgl.customer'].search(
            ['&', ('account_type', '=', 'Commingled'),('is_customer_billed', '=', True),
             ('is_account_closed', '=', False),  ('custodian_id', '=', new_direction_id)],
            order='account_type desc')
        filtered_customer_ids = []
        for customer in customers:
            first_order = self.env['amgl.order_line'].search(
                [('customer_id', '=', customer.id), ('metal_movement_id', '=', False),
                 ('is_master_records', '=', False)], order='date_received asc',
                limit=1)
            if first_order:
                billing_month = start_date.month
                billing_year = end_date.year
                first_order_month = datetime.datetime.strptime(first_order.date_received, '%Y-%m-%d').month
                year_difference = billing_year - datetime.datetime.strptime(first_order.date_received,
                                                                            '%Y-%m-%d').year
                first_order_year = (datetime.datetime.strptime(first_order.date_received,
                                                               '%Y-%m-%d') + relativedelta(years=year_difference)).year

                if first_order_month == billing_month and first_order_year == billing_year and year_difference > 0:
                    filtered_customer_ids.append(customer.id)
        existing_customers = self.env['amgl.customer'].search([('id', 'in', filtered_customer_ids)]).ids
        return existing_customers

    def get_existing_commingled_customer_for_storage_invoice_equity(self, start_date, end_date,
                                                                           new_direction_id):
        customers = self.env['amgl.customer'].search(
            ['&', ('account_type', '=', 'Commingled'),('is_customer_billed', '=', True),
             ('is_account_closed', '=', False),  ('custodian_id', '=', new_direction_id)],
            order='account_type desc')
        filtered_customer_ids = []
        for customer in customers:
            first_order = self.env['amgl.order_line'].search(
                [('customer_id', '=', customer.id), ('metal_movement_id', '=', False),
                 ('is_master_records', '=', False)], order='date_received asc',
                limit=1)
            if first_order:
                billing_month = start_date.month
                billing_year = end_date.year
                first_order_month = datetime.datetime.strptime(first_order.date_received, '%Y-%m-%d').month
                year_difference = billing_year - datetime.datetime.strptime(first_order.date_received,
                                                                            '%Y-%m-%d').year
                first_order_year = (datetime.datetime.strptime(first_order.date_received,
                                                               '%Y-%m-%d') + relativedelta(years=year_difference)).year

                if first_order_month == billing_month and first_order_year == billing_year and year_difference > 0:
                    filtered_customer_ids.append(customer.id)
        existing_customers = self.env['amgl.customer'].search([('id', 'in', filtered_customer_ids)]).ids
        return existing_customers

    def generate_new_accounts_invoice_for_new_direction(self, start_date, end_date, new_direction_id):
        result = ''
        file_name = ''
        attachment_id = 0
        if 'commingled' in self.report_types:
            new_customers = self.get_new_commingled_customer_for_storage_invoice_new_direction(
                start_date, end_date, new_direction_id)
            if 'excel' in self.report_format:
                attachment_id, file_name = self.create_excel_file_for_storage_invoice(start_date,end_date,new_customers,'commingled','new',str(self.custodian.name))
            else:
                result = self.new_direction_accounts_storage_invoice(new_customers, self.report_types, start_date)
        elif 'segregated' in self.report_types:
            new_customers = self.get_new_segregated_customer_for_storage_invoice_new_direction(
                start_date, end_date, new_direction_id)
            if 'excel' in self.report_format:
                attachment_id, file_name = self.create_excel_file_for_storage_invoice(start_date,end_date,  new_customers, 'segregated',
                                                                                      'new', str(self.custodian.name))
            else:
                result = self.new_direction_accounts_storage_invoice(new_customers, self.report_types, start_date)
        if len(new_customers) > 0 and self.bill_customers:
            self.update_customers(new_customers)
        return result,attachment_id, file_name

    def update_customers(self,customers):
        customer_ids = '('
        for customer in customers:
            customer_ids += str(customer) + ','
        customer_ids = customer_ids.rstrip(',')
        customer_ids += ')'
        self.env.cr.execute(
            "UPDATE amgl_customer set is_customer_billed = '" + 'True' + "' where id in " + str(
                customer_ids))

    def get_new_segregated_customer_for_storage_invoice_new_direction(self, start_date, end_date, new_direction_id):
        customers = self.env['amgl.customer'].search(
            ['&', ('account_type', '=', 'Segregated'), ('is_account_closed', '=', False), ('custodian_id', '=', new_direction_id),
             ('customer_first_deposit_date', '>=', start_date), ('customer_first_deposit_date', '<=', end_date),
             ('is_customer_billed', '=', False),('customer_first_deposit_date', '!=', '2000-01-01')],
            order='account_type desc')
        filtered_customer_ids = []
        for customer in customers:
            # if customer.grace_period:
            #     customer_order_lines = self.env['amgl.order_line'].search(
            #         ['&', ('customer_id', '=', customer.id), ('is_master_records', '=', False)],
            #         order='date_received asc')
            #     if customer_order_lines:
            #         first_deposit_date = customer_order_lines[0].date_received
            #         temp_end_of_period = parser.parse(first_deposit_date) + relativedelta(
            #             months=customer.grace_period)
            #         end_of_period = parser.parse(str(temp_end_of_period)).date()
            #         today_date = datetime.datetime.now().date()
            #         if today_date <= end_of_period:
            #             continue

            # customer_orders = self.env['amgl.order_line'].search(
            #     ['&', ('customer_id', '=', customer.id), ('metal_movement_id', '=', False),
            #      ('is_master_records', '=', False)], order='date_received asc')
            # customer_allowed_on_report = False
            # for order in customer_orders:
            #     date_received = datetime.datetime.strptime(order.date_for_customer_metal_activitiy, '%Y-%m-%d')
            #     if date_received >= start_date and date_received <= end_date:
            #         customer_allowed_on_report = True
            #     else:
            #         customer_allowed_on_report = False
            #         break;
            # if customer_allowed_on_report:
            filtered_customer_ids.append(customer.id)
        if self.bill_customers and len(filtered_customer_ids) == 0:
            customers = self.env['amgl.customer'].search(
                ['&', ('account_type', '=', 'Segregated'), ('is_account_closed', '=', False),
                 ('custodian_id', '=', new_direction_id),
                 ('customer_first_deposit_date', '>=', start_date), ('customer_first_deposit_date', '<=', end_date),
                 ('is_customer_billed', '=', True), ('customer_first_deposit_date', '!=', '2000-01-01')],
                order='account_type desc')
            if len(customers) > 0:
                raise ValidationError("Inovice for the selection has already been submitted!")
        new_customers = self.env['amgl.customer'].search([('id', 'in', filtered_customer_ids)]).ids
        return new_customers

    def get_new_commingled_customer_for_storage_invoice_new_direction(self, start_date, end_date, new_direction_id):
        customers = self.env['amgl.customer'].search(
            ['&', ('account_type', '=', 'Commingled'),('is_account_closed', '=', False), ('custodian_id', '=', new_direction_id),
             ('customer_first_deposit_date', '>=', start_date), ('customer_first_deposit_date', '<=', end_date),
             ('is_customer_billed', '=', False),('customer_first_deposit_date', '!=', '2000-01-01')],
            order='account_type desc')
        filtered_customer_ids = []
        for customer in customers:
            # if customer.grace_period:
            #     customer_order_lines = self.env['amgl.order_line'].search(
            #         ['&', ('customer_id', '=', customer.id), ('is_master_records', '=', False),
            #          ('date_received', '>=', start_date)
            #             , ('date_received', '<=', end_date)],
            #         order='date_received asc')
            #     if customer_order_lines:
            #         first_deposit_date = customer_order_lines[0].date_received
            #         temp_end_of_period = parser.parse(first_deposit_date) + relativedelta(
            #             months=customer.grace_period)
            #         end_of_period = parser.parse(str(temp_end_of_period)).date()
            #         today_date = datetime.datetime.now().date()
            #         if today_date <= end_of_period:
            #             continue

            # customer_orders = self.env['amgl.order_line'].search(
            #     ['&', ('customer_id', '=', customer.id), ('metal_movement_id', '=', False),
            #      ('is_master_records', '=', False)], order='date_received asc')
            # customer_allowed_on_report = False
            # for order in customer_orders:
            #     date_received = datetime.datetime.strptime(order.date_for_customer_metal_activitiy, '%Y-%m-%d')
            #     if date_received >= start_date and date_received <= end_date:
            #         customer_allowed_on_report = True
            #     else:
            #         customer_allowed_on_report = False
            #         break;
            # if customer_allowed_on_report:
            filtered_customer_ids.append(customer.id)
        if self.bill_customers and len(filtered_customer_ids) == 0:
            customers = self.env['amgl.customer'].search(
                ['&', ('account_type', '=', 'Commingled'), ('is_account_closed', '=', False),
                 ('custodian_id', '=', new_direction_id),
                 ('customer_first_deposit_date', '>=', start_date), ('customer_first_deposit_date', '<=', end_date),
                 ('is_customer_billed', '=', True), ('customer_first_deposit_date', '!=', '2000-01-01')],
                order='account_type desc')
            if len(customers) > 0:
                raise ValidationError("Inovice for the selection has already been submitted!")


        new_customers = self.env['amgl.customer'].search([('id', 'in', filtered_customer_ids)]).ids
        return new_customers

    def add_report_to_attachment(self, report_result, report_name):
        attachment = self.env['ir.attachment'].create({'name': report_name,
                                                       'datas': base64.b64encode(report_result),
                                                       'datas_fname': report_name,
                                                       'res_model': 'res.users',
                                                       'res_id': 1, })
        return attachment

    @api.multi
    def gold_star_accounts_storage_invoice(self, customers, report_type, start_date):
        report_name = ''
        if 'commingled' in report_type and 'existing' in report_type:
            report_name = 'amgl.existing_accounts_billing_commingled_gold_star'
        if 'segregated' in report_type and 'existing' in report_type:
            report_name = 'amgl.existing_accounts_billing_segregated_gold_star'
        if 'commingled' in report_type and 'new_accounts' in report_type:
            report_name = 'amgl.new_accounts_billing_report_commingled_gold_star'
        if 'segregated' in report_type and 'new_accounts' in report_type:
            report_name = 'amgl.new_accounts_billing_report_segregated_gold_star'

        data_object = {
            'ids': customers,
            'model': 'amgl.customer',
            'form': customers
        }
        if 'existing' in report_type:
            context = dict(self.env.context,
                           selected_date=str(calendar.month_name[int(start_date.month)]) + ", " + str(start_date.year))
        else:
            context = dict(self.env.context,
                           selected_date=str(calendar.month_name[start_date.month]) + ", " + str(start_date.year))
        return {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': data_object,
            'context': context
        }
        # report_result = self.env['report'].get_pdf(customers, report_name, data=data_object)
        # attachment = self.add_report_to_attachment(report_result, 'New Accounts Billing')
        # self.upload_file(attachment,True)

    @api.multi
    def new_direction_accounts_storage_invoice(self, customers, report_type, start_date):
        report_name = ''
        if 'New Direction' in str(self.custodian.name):
            if 'commingled' in report_type and 'existing' in report_type:
                report_name = 'amgl.new_direction_existing_accounts_billing_commingled'
            if 'segregated' in report_type and 'existing' in report_type:
                report_name = 'amgl.new_direction_existing_accounts_billing_segregated'
            if 'commingled' in report_type and 'new_accounts' in report_type:
                report_name = 'amgl.new_direction_new_accounts_billing_commingled'
            if 'segregated' in report_type and 'new_accounts' in report_type:
                report_name = 'amgl.new_direction_new_accounts_billing_segregated'

        if 'Equity' in str(self.custodian.name):
            if 'commingled' in report_type and 'existing' in report_type:
                report_name = 'amgl.equity_existing_accounts_billing_commingled'
            if 'segregated' in report_type and 'existing' in report_type:
                report_name = 'amgl.equity_existing_accounts_billing_segregated'
            if 'commingled' in report_type and 'new_accounts' in report_type:
                report_name = 'amgl.equity_new_accounts_billing_commingled'
            if 'segregated' in report_type and 'new_accounts' in report_type:
                report_name = 'amgl.equity_new_accounts_billing_segregated'

        data_object = {
            'ids': customers,
            'model': 'amgl.customer',
            'form': customers
        }
        if 'existing' in report_type:
            context = dict(self.env.context,
                           selected_date=str(calendar.month_name[int(start_date.month)]) + ", " + str(start_date.year))
        else:
            context = dict(self.env.context,
                           selected_date=str(calendar.month_name[start_date.month]) + ", " + str(start_date.year))
        return {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': data_object,
            'context': context
        }
        # report_result = self.env['report'].get_pdf(customers, report_name, data=data_object)
        # attachment = self.add_report_to_attachment(report_result, 'New Accounts Billing')
        # self.upload_file(attachment,True)

    # region Provident Trust Group Billing Reports pdf

    def generate_new_accounts_invoice_for_provident_trust(self, start_date, end_date, provident_trust_id):
        result = ''
        file_name = ''
        attachment_id = 0
        if 'commingled' in self.report_types:
            new_customers = self.get_new_commingled_customer_for_storage_invoice_provident_trust(start_date, end_date, provident_trust_id)
            if 'excel' in self.report_format:
                attachment_id,file_name = self.create_excel_file_for_storage_invoice(start_date, end_date,new_customers,'commingled','new','Provident Trust')
            else:
                result = self.provident_trust_accounts_storage_invoice(new_customers, self.report_types, start_date)
        elif 'segregated' in self.report_types:
            new_customers = self.get_new_segregated_customer_for_storage_invoice_provident_trust(start_date, end_date, provident_trust_id)
            if 'excel' in self.report_format:
                attachment_id,file_name = self.create_excel_file_for_storage_invoice(start_date, end_date,new_customers,'segregated','new','Provident Trust')
            else:
                result = self.provident_trust_accounts_storage_invoice(new_customers, self.report_types, start_date)
        if len(new_customers) > 0 and self.bill_customers:
            self.update_customers(new_customers)
        return result,attachment_id,file_name

    def get_new_commingled_customer_for_storage_invoice_provident_trust(self, start_date, end_date, provident_trust_id):
        customers = self.env['amgl.customer'].search(
            ['&', ('account_type', '=', 'Commingled'), ('is_account_closed', '=', False), ('custodian_id', '=', provident_trust_id),
             ('customer_first_deposit_date', '>=', start_date), ('customer_first_deposit_date', '<=', end_date),
             ('is_customer_billed', '=', False),('customer_first_deposit_date', '!=', '2000-01-01')],
            order='account_type desc')
        filtered_customer_ids = []
        for customer in customers:
            # if customer.grace_period:
            #     customer_order_lines = self.env['amgl.order_line'].search(
            #         ['&', ('customer_id', '=', customer.id), ('is_master_records', '=', False),
            #          ('date_received', '>=', start_date)
            #             , ('date_received', '<=', end_date)],
            #         order='date_received asc')
            #     if customer_order_lines:
            #         first_deposit_date = customer_order_lines[0].date_received
            #         temp_end_of_period = parser.parse(first_deposit_date) + relativedelta(
            #             months=customer.grace_period)
            #         end_of_period = parser.parse(str(temp_end_of_period)).date()
            #         today_date = datetime.datetime.now().date()
            #         if today_date <= end_of_period:
            #             continue

            # customer_orders = self.env['amgl.order_line'].search(
            #     ['&', ('customer_id', '=', customer.id), ('metal_movement_id', '=', False),
            #      ('is_master_records', '=', False)], order='date_received asc')
            # customer_allowed_on_report = False
            # for order in customer_orders:
            #     date_received = datetime.datetime.strptime(order.date_for_customer_metal_activitiy, '%Y-%m-%d')
            #     if date_received >= start_date and date_received <= end_date:
            #         customer_allowed_on_report = True
            #     else:
            #         customer_allowed_on_report = False
            #         break;
            # if customer_allowed_on_report:
            filtered_customer_ids.append(customer.id)
        if self.bill_customers and len(filtered_customer_ids) == 0:
            customers = self.env['amgl.customer'].search(
                ['&', ('account_type', '=', 'Commingled'), ('is_account_closed', '=', False),
                 ('custodian_id', '=', provident_trust_id),
                 ('customer_first_deposit_date', '>=', start_date), ('customer_first_deposit_date', '<=', end_date),
                 ('is_customer_billed', '=', True), ('customer_first_deposit_date', '!=', '2000-01-01')],
                order='account_type desc')
            if len(customers) > 0:
                raise ValidationError("Inovice for the selection has already been submitted!")
        new_customers = self.env['amgl.customer'].search([('id', 'in', filtered_customer_ids)]).ids
        return new_customers

    def get_new_segregated_customer_for_storage_invoice_provident_trust(self, start_date, end_date, provident_trust_id):
        customers = self.env['amgl.customer'].search(
            ['&', ('account_type', '=', 'Segregated'), ('is_account_closed', '=', False), ('custodian_id', '=', provident_trust_id),
             ('customer_first_deposit_date', '>=', start_date), ('customer_first_deposit_date', '<=', end_date),
             ('is_customer_billed', '=', False),('customer_first_deposit_date', '!=', '2000-01-01')],
            order='account_type desc')
        filtered_customer_ids = []
        for customer in customers:
            # if customer.grace_period:
            #     customer_order_lines = self.env['amgl.order_line'].search(
            #         ['&', ('customer_id', '=', customer.id), ('is_master_records', '=', False)],
            #         order='date_received asc')
            #     if customer_order_lines:
            #         first_deposit_date = customer_order_lines[0].date_received
            #         temp_end_of_period = parser.parse(first_deposit_date) + relativedelta(
            #             months=customer.grace_period)
            #         end_of_period = parser.parse(str(temp_end_of_period)).date()
            #         today_date = datetime.datetime.now().date()
            #         if today_date <= end_of_period:
            #             continue

            # customer_orders = self.env['amgl.order_line'].search(
            #     ['&', ('customer_id', '=', customer.id), ('metal_movement_id', '=', False),
            #      ('is_master_records', '=', False)], order='date_received asc')
            # customer_allowed_on_report = False
            # for order in customer_orders:
            #     date_received = datetime.datetime.strptime(order.date_for_customer_metal_activitiy, '%Y-%m-%d')
            #     if date_received >= start_date and date_received <= end_date:
            #         customer_allowed_on_report = True
            #     else:
            #         customer_allowed_on_report = False
            #         break;
            # if customer_allowed_on_report:
            filtered_customer_ids.append(customer.id)
        if self.bill_customers and len(filtered_customer_ids) == 0:
            customers = self.env['amgl.customer'].search(
                ['&', ('account_type', '=', 'Segregated'), ('is_account_closed', '=', False),
                 ('custodian_id', '=', provident_trust_id),
                 ('customer_first_deposit_date', '>=', start_date), ('customer_first_deposit_date', '<=', end_date),
                 ('is_customer_billed', '=', True), ('customer_first_deposit_date', '!=', '2000-01-01')],
                order='account_type desc')
            if len(customers) > 0:
                raise ValidationError("Inovice for the selection has already been submitted!")
        new_customers = self.env['amgl.customer'].search([('id', 'in', filtered_customer_ids)]).ids
        return new_customers

    def generate_existing_accounts_invoice_for_provident_trust(self, start_date, end_date, provident_trust_id):
        result = ''
        file_name = ''
        attachment_id = 0
        if 'commingled' in self.report_types:
            existing_customers = self.get_existing_commingled_customer_for_storage_invoice_provident_trust(start_date,
                                                                                                         end_date,
                                                                                                         provident_trust_id)
            if 'excel' in self.report_format:
                attachment_id,file_name = self.create_excel_file_for_storage_invoice(start_date, end_date,existing_customers,'commingled','existing','Provident Trust')
            else:
                result = self.provident_trust_accounts_storage_invoice(existing_customers, self.report_types, start_date)
        elif 'segregated' in self.report_types:
            existing_customers = self.get_existing_segregated_customer_for_storage_invoice_provident_trust(start_date,
                                                                                                         end_date,
                                                                                                         provident_trust_id)
            if 'excel' in self.report_format:
                attachment_id, file_name = self.create_excel_file_for_storage_invoice(start_date, end_date,existing_customers,'segregated','existing','Provident Trust')
            else:
                result = self.provident_trust_accounts_storage_invoice(existing_customers, self.report_types, start_date)
        return result,attachment_id,file_name

    def get_existing_segregated_customer_for_storage_invoice_provident_trust(self, start_date, end_date,
                                                                             provident_trust_id):
        customers = self.env['amgl.customer'].search(
            ['&', ('account_type', '=', 'Segregated'), ('is_account_closed', '=', False),('is_customer_billed', '=', True), ('custodian_id', '=', provident_trust_id)],
            order='account_type desc')
        filtered_customer_ids = []
        for customer in customers:
            first_order = self.env['amgl.order_line'].search(
                [('customer_id', '=', customer.id), ('metal_movement_id', '=', False),
                 ('is_master_records', '=', False)], order='date_received asc',
                limit=1)
            if first_order:
                billing_month = start_date.month
                billing_year = end_date.year
                first_order_month = datetime.datetime.strptime(first_order.date_received, '%Y-%m-%d').month
                year_difference = billing_year - datetime.datetime.strptime(first_order.date_received,
                                                                            '%Y-%m-%d').year
                first_order_year = (datetime.datetime.strptime(first_order.date_received,
                                                               '%Y-%m-%d') + relativedelta(years=year_difference)).year

                if first_order_month == billing_month and first_order_year == billing_year and year_difference > 0:
                    filtered_customer_ids.append(customer.id)
        existing_customers = self.env['amgl.customer'].search([('id', 'in', filtered_customer_ids)]).ids
        return existing_customers
    def get_existing_commingled_customer_for_storage_invoice_provident_trust(self, start_date, end_date,
                                                                             provident_trust_id):
        customers = self.env['amgl.customer'].search(
            ['&', ('account_type', '=', 'Commingled'),('is_customer_billed', '=', True), ('is_account_closed', '=', False), ('custodian_id', '=', provident_trust_id)],
            order='account_type desc')
        filtered_customer_ids = []
        for customer in customers:
            first_order = self.env['amgl.order_line'].search(
                [('customer_id', '=', customer.id), ('metal_movement_id', '=', False),
                 ('is_master_records', '=', False)], order='date_received asc',
                limit=1)
            if first_order:
                billing_month = start_date.month
                billing_year = end_date.year
                first_order_month = datetime.datetime.strptime(first_order.date_received, '%Y-%m-%d').month
                year_difference = billing_year - datetime.datetime.strptime(first_order.date_received,
                                                                            '%Y-%m-%d').year
                first_order_year = (datetime.datetime.strptime(first_order.date_received,
                                                               '%Y-%m-%d') + relativedelta(years=year_difference)).year

                if first_order_month == billing_month and first_order_year == billing_year and year_difference > 0:
                    filtered_customer_ids.append(customer.id)
        existing_customers = self.env['amgl.customer'].search([('id', 'in', filtered_customer_ids)]).ids
        return existing_customers
    @api.multi
    def provident_trust_accounts_storage_invoice(self, customers, report_type, start_date):
        report_name = ''
        if 'commingled' in report_type and 'existing' in report_type:
            report_name = 'amgl.provident_trust_existing_accounts_billing_commingled'
        if 'segregated' in report_type and 'existing' in report_type:
            report_name = 'amgl.provident_trust_existing_accounts_billing_segregated'
        if 'commingled' in report_type and 'new_accounts' in report_type:
            report_name = 'amgl.provident_trust_new_accounts_billing_commingled'
        if 'segregated' in report_type and 'new_accounts' in report_type:
            report_name = 'amgl.provident_trust_new_accounts_billing_segregated'

        data_object = {
            'ids': customers,
            'model': 'amgl.customer',
            'form': customers
        }
        if 'existing' in report_type:
            context = dict(self.env.context,
                           selected_date=str(calendar.month_name[int(start_date.month)]) + ", " + str(start_date.year))
        else:
            context = dict(self.env.context,
                           selected_date=str(calendar.month_name[start_date.month]) + ", " + str(start_date.year))
        return {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': data_object,
            'context': context
        }


    #endregion

    # region Excel Versions For All Billing Invoices

    def create_custodian_inventory_for_product(self, account_type):
        if 'commingled' in account_type:
            report_name = 'Custodian Inventory By Product - Commingled'
        if 'segregated' in account_type:
            report_name = 'Custodian Inventory By Product - Segregated'
        if 'full' in account_type:
            report_name = 'Custodian Inventory By Product (Full)'
        bold, file_name, workbook, worksheet = self.configure_workbook_for_custodian_inventory_for_product(report_name)
        Reports.add_headers_for_custodian_inventory_for_product(bold, worksheet, self.custodian.name, account_type)
        total_cells_format = workbook.add_format({'bold': True})
        total_cells_format.set_border(1)
        is_data_exists = False
        if 'commingled' in account_type:
            is_data_exists = self.add_rows_in_worksheet_for_custodian_inventory_for_product(bold, worksheet, workbook, 'Commingled')
        if 'segregated' in account_type:
            is_data_exists = self.add_rows_in_worksheet_for_custodian_inventory_for_product(bold, worksheet, workbook, 'Segregated')
        if 'full' in account_type:
            is_data_exists = self.add_rows_in_worksheet_for_custodian_inventory_for_product(bold, worksheet, workbook, '')

        workbook.close()
        if is_data_exists:
            attachment = self.add_file_in_attachment(file_name)
        return attachment, file_name

    def create_excel_file_for_storage_invoice(self, start_date, end_date, customres, account_type, account_stage,
                                              custodian_name):
        report_name = self.get_report_name(account_type, account_stage, custodian_name)
        bold, file_name, workbook, worksheet = self.configure_workbook_for_storage_invoices(report_name)
        Reports.add_headers_for_storage_invoices(bold, worksheet)
        row_count = 2
        attachment_id = 0
        total_cells_format = workbook.add_format({'bold': True})
        total_cells_format.set_border(1)
        is_data_exists = self.add_rows_in_worksheet_for_storage_invoices(bold, row_count, worksheet, start_date,
                                                                         end_date, workbook, customres)
        workbook.close()
        if is_data_exists:
            attachment = self.add_file_in_attachment(file_name)
            attachment_id = attachment.id
        return attachment_id, file_name

    def configure_workbook_for_custodian_inventory_for_product(self, report_name):
        file_name = "/excel/" + report_name + '.xlsx'
        workbook = xlsxwriter.Workbook(file_name)
        worksheet = workbook.add_worksheet('Custodian Inventory')
        bold = workbook.add_format({'bold': True})
        return bold, file_name, workbook, worksheet

    def configure_workbook_for_storage_invoices(self, report_name):
        file_name = "/excel/" + report_name + '.xlsx'
        workbook = xlsxwriter.Workbook(file_name)
        worksheet = workbook.add_worksheet('Storage Invoice')
        bold = workbook.add_format({'bold': True})
        return bold, file_name, workbook, worksheet

    def get_report_name(self, account_type, account_stage, custodian_name):

        report_name = ''
        if account_type == 'commingled' and account_stage == 'existing' and custodian_name == 'Provident Trust':
            report_name = ' Provident Trust Group - Existing Accounts Commingled Invoice'
        elif account_type == 'commingled' and account_stage == 'new' and custodian_name == 'Provident Trust':
            report_name = ' Provident Trust Group - New Accounts Commingled Invoice'
        elif account_type == 'segregated' and account_stage == 'existing' and custodian_name == 'Provident Trust':
            report_name = ' Provident Trust Group - Existing Accounts Segregated Invoice'
        elif account_type == 'segregated' and account_stage == 'new' and custodian_name == 'Provident Trust':
            report_name = ' Provident Trust Group - New Accounts Segregated Invoice'

        elif account_type == 'commingled' and account_stage == 'new' and custodian_name == 'New Direction':
            report_name = ' New Direction Trust Company - New Accounts Commingled Invoice'
        elif account_type == 'segregated' and account_stage == 'existing' and custodian_name == 'New Direction':
            report_name = ' New Direction Trust Company - Existing Accounts Segregated Invoice'
        elif account_type == 'segregated' and account_stage == 'new' and custodian_name == 'New Direction':
            report_name = ' New Direction Trust Company - New Accounts Segregated Invoice'
        elif account_type == 'commingled' and account_stage == 'existing' and custodian_name == 'New Direction':
            report_name = ' New Direction Trust Company - Existing Accounts Commingled Invoice'

        elif account_type == 'commingled' and account_stage == 'new' and 'Equity' in custodian_name:
            report_name = ' Equity Trust Company - New Accounts Commingled Invoice'
        elif account_type == 'segregated' and account_stage == 'existing' and 'Equity' in custodian_name:
            report_name = ' Equity Trust Company - Existing Accounts Segregated Invoice'
        elif account_type == 'segregated' and account_stage == 'new' and 'Equity' in custodian_name:
            report_name = ' Equity Trust Company - New Accounts Segregated Invoice'
        elif account_type == 'commingled' and account_stage == 'existing' and 'Equity' in custodian_name:
            report_name = ' Equity Trust Company - Existing Accounts Commingled Invoice'

        elif account_type == 'commingled' and account_stage == 'new' and custodian_name == 'GoldStar':
            report_name = ' GoldStar Trust Company - New Accounts Commingled Invoice'
        elif account_type == 'segregated' and account_stage == 'existing' and custodian_name == 'GoldStar':
            report_name = ' GoldStar Trust Company - Existing Accounts Segregated Invoice'
        elif account_type == 'segregated' and account_stage == 'new' and custodian_name == 'GoldStar':
            report_name = ' GoldStar Trust Company - New Accounts Segregated Invoice'
        elif account_type == 'commingled' and account_stage == 'existing' and custodian_name == 'GoldStar':
            report_name = ' GoldStar Trust Company - Existing Accounts Commingled Invoice'

        return report_name

    def add_rows_in_worksheet_for_storage_invoices(self, bold, row_count, worksheet, start_date, end_date, workbook,
                                                   customers):

        row_count = 3
        column_count = 0
        custodian_address = self.get_custodian_address()
        account_stage = self.get_account_stage()
        account_type = self.get_account_type()
        worksheet.write(row_count, column_count, 'Bill To:', bold)
        worksheet.write(row_count, column_count + 1, custodian_address[0])
        worksheet.write(row_count + 1, column_count + 1, custodian_address[1])
        worksheet.write(row_count + 2, column_count + 1, custodian_address[2])
        worksheet.write(row_count + 3, column_count + 1, custodian_address[3])
        worksheet.write(row_count, column_count + 5, 'Invoice:', bold)
        worksheet.write(row_count, column_count + 6, 'Storage, ' + account_stage + 'Accounts')
        row_count += 1
        worksheet.write(row_count, column_count + 5, 'Billing Month:', bold)
        worksheet.write(row_count, column_count + 6,
                        str(calendar.month_name[int(start_date.month)]) + ", " + str(start_date.year))
        row_count += 1
        worksheet.write(row_count, column_count + 5, 'Issued Date:', bold)
        worksheet.write(row_count, column_count + 6, str(
            datetime.datetime.strptime(str(datetime.datetime.now().date()), '%Y-%m-%d').strftime("%m/%d/%Y")))
        row_count += 2
        worksheet.write(row_count + 1, column_count + 2, account_type, bold)

        row_count = 12
        column_count = 0
        format_for_numeric_without_bold = workbook.add_format({'align': 'right'})
        format_for_numeric_bold = workbook.add_format({'bold': True, 'align': 'right', })
        total_fees = 0.0
        for customer in customers:
            customer_info = self.env['amgl.customer'].search([('id', '=', customer)])
            total_weight, account_value, account_fees = self.calculate_and_filter_customer_inventory(customer,
                                                                                                     start_date)
            if account_fees <= 0:
                account_fees = 0.00
            worksheet.write(row_count, column_count,
                            customer_info.account_number if 'Gold' not in customer_info.custodian_id.name else customer_info.gst_account_number)
            column_count += 1
            worksheet.write(row_count, column_count, self.get_init_deposit_date(customer))
            column_count += 1
            worksheet.write(row_count, column_count, customer_info.full_name)
            column_count += 1
            worksheet.write(row_count, column_count, str('{0:,.2f}'.format(total_weight)) + ' oz',
                            format_for_numeric_without_bold)
            column_count += 1
            worksheet.write(row_count, column_count, '$ ' + str('{0:,.2f}'.format(account_value)),
                            format_for_numeric_without_bold)
            column_count += 1
            worksheet.write(row_count, column_count, '$ ' + str('{0:,.2f}'.format(account_fees)),
                            format_for_numeric_without_bold)
            column_count += 1
            total_fees += account_fees
            row_count += 1
            column_count = 0

        row_count += 3
        column_count = 0

        worksheet.write(row_count, column_count, 'Total ' + account_stage + ' ' + account_type + ' ' + 'Accounts:',
                        bold)
        worksheet.write(row_count, column_count + 1, len(customers))

        worksheet.write(row_count, column_count + 4, 'Grand Total: ', bold)
        worksheet.write(row_count, column_count + 5, '$' + str(total_fees), format_for_numeric_without_bold)

        return True

    def add_rows_in_worksheet_for_custodian_inventory_for_product(self, bold, worksheet, workbook, account_type):

        row_count = 9
        column_count = 0
        format_for_numeric_without_bold = workbook.add_format({'align': 'right'})
        is_gold_header_rendered = False;
        is_silver_header_rendered = False;
        is_platinum_header_rendered = False;
        is_palladium_header_rendered = False;

        gold_product_names = self.get_products('Gold')
        silver_product_names = self.get_products('Silver')
        platinum_product_names = self.get_products('Platinum')
        palladium_product_names = self.get_products('Palladium')

        if len(gold_product_names) > 0:
            for product_name in gold_product_names:
                _product = self.env['amgl.products'].search([('goldstar_name', '=', product_name)], limit=1)

                qty = self.get_products_total_quantity(product_name, self.custodian.name, account_type)
                if qty > 0:
                    if is_gold_header_rendered is False:
                        worksheet.write(row_count, 0, 'Commodity : Gold', bold)
                        is_gold_header_rendered = True;
                        row_count += 1
                        worksheet.write(row_count, 0, 'Product Code', bold)
                        worksheet.write(row_count, 1, 'Product Description', bold)
                        worksheet.write(row_count, 2, 'Units', bold)
                        worksheet.write(row_count, 3, 'Ounce Conversion', bold)
                        worksheet.write(row_count, 4, 'Ounces', bold)
                        row_count += 1

                    worksheet.write(row_count, column_count, _product.product_code)
                    column_count += 1
                    worksheet.write(row_count, column_count, _product.name)
                    column_count += 1
                    worksheet.write(row_count, column_count, qty, format_for_numeric_without_bold)
                    column_count += 1
                    if _product.weight_unit == 'oz':
                        worksheet.write(row_count, column_count, _product.weight_per_piece)
                    if _product.weight_unit == 'gram':
                        worksheet.write(row_count, column_count, _product.weight_per_piece * 0.03215)
                    if _product.weight_unit == 'kg':
                        worksheet.write(row_count, column_count, _product.weight_per_piece * 32.15)
                    if _product.weight_unit == 'pounds':
                        worksheet.write(row_count, column_count, _product.weight_per_piece * 16)
                    column_count += 1
                    worksheet.write(row_count, column_count, _product.weight_per_piece * qty,
                                    format_for_numeric_without_bold)
                    row_count += 1
                    column_count = 0
        row_count += 2

        if len(silver_product_names) > 0:

            for product_name in silver_product_names:
                _product = self.env['amgl.products'].search([('goldstar_name', '=', product_name)], limit=1)

                qty = self.get_products_total_quantity(product_name, self.custodian.name, account_type)
                if qty > 0:
                    if is_silver_header_rendered is False:
                        worksheet.write(row_count, 0, 'Commodity : Silver', bold)
                        is_silver_header_rendered = True;
                        row_count += 1
                        worksheet.write(row_count, 0, 'Product Code', bold)
                        worksheet.write(row_count, 1, 'Product Description', bold)
                        worksheet.write(row_count, 2, 'Units', bold)
                        worksheet.write(row_count, 3, 'Ounce Conversion', bold)
                        worksheet.write(row_count, 4, 'Ounces', bold)
                        row_count += 1

                    worksheet.write(row_count, column_count, _product.product_code)
                    column_count += 1
                    worksheet.write(row_count, column_count, _product.name)
                    column_count += 1
                    worksheet.write(row_count, column_count, qty, format_for_numeric_without_bold)
                    column_count += 1
                    if _product.weight_unit == 'oz':
                        worksheet.write(row_count, column_count, _product.weight_per_piece)
                    if _product.weight_unit == 'gram':
                        worksheet.write(row_count, column_count, _product.weight_per_piece * 0.03215)
                    if _product.weight_unit == 'kg':
                        worksheet.write(row_count, column_count, _product.weight_per_piece * 32.15)
                    if _product.weight_unit == 'pounds':
                        worksheet.write(row_count, column_count, _product.weight_per_piece * 16)
                    column_count += 1
                    worksheet.write(row_count, column_count, _product.weight_per_piece * qty,
                                    format_for_numeric_without_bold)

                    row_count += 1
                    column_count = 0
        row_count += 2

        if len(platinum_product_names) > 0:
            for product_name in platinum_product_names:
                _product = self.env['amgl.products'].search([('goldstar_name', '=', product_name)], limit=1)

                qty = self.get_products_total_quantity(product_name, self.custodian.name, account_type)
                if qty > 0:
                    if is_platinum_header_rendered is False:
                        worksheet.write(row_count, 0, 'Commodity : Platinum', bold)
                        is_platinum_header_rendered = True;
                        row_count += 1
                        worksheet.write(row_count, 0, 'Product Code', bold)
                        worksheet.write(row_count, 1, 'Product Description', bold)
                        worksheet.write(row_count, 2, 'Units', bold)
                        worksheet.write(row_count, 3, 'Ounce Conversion', bold)
                        worksheet.write(row_count, 4, 'Ounces', bold)
                        row_count += 1

                    worksheet.write(row_count, column_count, _product.product_code)
                    column_count += 1
                    worksheet.write(row_count, column_count, _product.name)
                    column_count += 1
                    worksheet.write(row_count, column_count, qty, format_for_numeric_without_bold)
                    column_count += 1
                    if _product.weight_unit == 'oz':
                        worksheet.write(row_count, column_count, _product.weight_per_piece)
                    if _product.weight_unit == 'gram':
                        worksheet.write(row_count, column_count, _product.weight_per_piece * 0.03215)
                    if _product.weight_unit == 'kg':
                        worksheet.write(row_count, column_count, _product.weight_per_piece * 32.15)
                    if _product.weight_unit == 'pounds':
                        worksheet.write(row_count, column_count, _product.weight_per_piece * 16)
                    column_count += 1
                    worksheet.write(row_count, column_count, _product.weight_per_piece * qty,
                                    format_for_numeric_without_bold)

                    row_count += 1
                    column_count = 0
        row_count += 2

        if len(palladium_product_names) > 0:

            for product_name in palladium_product_names:
                _product = self.env['amgl.products'].search([('goldstar_name', '=', product_name)], limit=1)

                qty = self.get_products_total_quantity(product_name, self.custodian.name, account_type)
                if qty > 0:
                    if is_palladium_header_rendered is False:
                        worksheet.write(row_count, 0, 'Commodity : Palladium', bold)
                        is_palladium_header_rendered = True;
                        row_count +=1
                        worksheet.write(row_count, 0, 'Product Code', bold)
                        worksheet.write(row_count, 1, 'Product Description', bold)
                        worksheet.write(row_count, 2, 'Units', bold)
                        worksheet.write(row_count, 3, 'Ounce Conversion', bold)
                        worksheet.write(row_count, 4, 'Ounces', bold)
                        row_count += 1

                    worksheet.write(row_count, column_count, _product.product_code)
                    column_count += 1
                    worksheet.write(row_count, column_count, _product.name)
                    column_count += 1
                    worksheet.write(row_count, column_count, qty, format_for_numeric_without_bold)
                    column_count += 1
                    if _product.weight_unit == 'oz':
                        worksheet.write(row_count, column_count, _product.weight_per_piece)
                    if _product.weight_unit == 'gram':
                        worksheet.write(row_count, column_count, _product.weight_per_piece * 0.03215)
                    if _product.weight_unit == 'kg':
                        worksheet.write(row_count, column_count, _product.weight_per_piece * 32.15)
                    if _product.weight_unit == 'pounds':
                        worksheet.write(row_count, column_count, _product.weight_per_piece * 16)
                    column_count += 1
                    worksheet.write(row_count, column_count, _product.weight_per_piece * qty,
                                    format_for_numeric_without_bold)

                    row_count += 1
                    column_count = 0
        row_count += 2

        return True if row_count > 9 else False

    def get_custodian_address(self):
        if 'GoldStar' in self.custodian.name:
            return ['GoldStar Trust Company', '1401 West 4th Ave.', 'Canyon TX 79015', '']
        elif 'New Direction' in self.custodian.name:
            return ['New Direction Trust Company', '1070 W. Century Dr., #101', 'Louisville, CO 80027', '']
        elif 'Provident' in self.custodian.name:
            return ['Provident Trust Group', '8880 W. Sunset Rd.', 'Suite 250', 'Las Vegas, NV 89148']
        elif 'Equity' in str(self.custodian.name):
            return ['Equity Trust Company', '1 Equity Way', 'WestLake, OH 44145','']

    def get_account_stage(self):
        if 'new_accounts' in self.report_types:
            return 'New'
        elif 'existing_accounts' in self.report_types:
            return 'Existing'

    def get_account_type(self):
        if 'commingled' in self.report_types:
            return 'Non-Segregated'
        elif 'segregated' in self.report_types:
            return 'Segregated'

    def get_init_deposit_date(self, customer_id):
        first_order = self.env['amgl.order_line'].search(
            [('customer_id', '=', customer_id), ('metal_movement_id', '=', False),
             ('is_master_records', '=', False)], order='date_received asc', limit=1)
        if first_order:
            first_order_month = datetime.datetime.strptime(first_order.date_received, '%Y-%m-%d').month
            first_order_year = datetime.datetime.strptime(first_order.date_received, '%Y-%m-%d').year
            return str(calendar.month_name[first_order_month]) + ", " + str(first_order_year)
        else:
            return 'N/A'

    @staticmethod
    def add_headers_for_custodian_inventory_for_product(bold, worksheet, custodian_name, account_type):
        worksheet.write(1, 2, 'Custodian Inventory By Product', bold)
        worksheet.write(2, 2, custodian_name , bold)
        if 'commingled' in account_type:
            worksheet.write(3, 2, 'Commingled', bold)
        if 'segregated' in account_type:
            worksheet.write(3, 2, 'Segregated', bold)
        if '' == account_type:
            worksheet.write(3, 2, 'Commingled & Segregated', bold)

    @staticmethod
    def add_headers_for_storage_invoices(bold, worksheet):
        row_count = 11
        column_count = 0
        worksheet.write(row_count, column_count, 'Acc#', bold)
        worksheet.write(row_count, column_count + 1, 'Init Bill Date', bold)
        worksheet.write(row_count, column_count + 2, 'Account Name', bold)
        worksheet.write(row_count, column_count + 3, 'Total Ounces', bold)
        worksheet.write(row_count, column_count + 4, 'Account Value', bold)
        worksheet.write(row_count, column_count + 5, 'Fee', bold)

    def calculate_and_filter_customer_inventory(self, customer, date):
        gold_price, palladium_price, platinum_price, silver_price = self.get_spot_price_from_database()
        total_gold = total_silver = total_platinum = total_palladium = total = 0
        total_weight = gold_weight = silver_weight = platinum_weight = palladium_weight = 0
        customer_order_lines = self.get_customer_master_order_lines(customer)
        for line in customer_order_lines:
            for p in line.products:
                qty = self.calculate_quantity_for_existing_reports(customer, p.id, line.total_received_quantity)
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
        customer_info = self.env['amgl.customer'].search([('id', '=', customer)])
        account_fees = self.calculate_account_storage_fees(account_fees,
                                                           account_value, self.custodian.name,
                                                           customer_info.account_type)
        return [total_weight, round(account_value, 2), round(account_fees, 2)]

    def get_spot_price_from_database(self):

        month = str(calendar.month_name[int(self.month)])
        spot_price_object = self.env['amgl.closing.rates'].search(
            [('month', '=', month), ('years', '=', str(self.year))])
        return spot_price_object.gold_rate, spot_price_object.palladium_rate, \
               spot_price_object.platinum_rate, spot_price_object.silver_rate

    def get_customer_master_order_lines(self, customer):
        customer_master_order_lines = self.env['amgl.order_line'].search([('customer_id', '=', customer),
                                                                          ('is_master_records', '=', True),
                                                                          ('is_active', '=', True)])
        filtered_order_lines = []
        if customer_master_order_lines:
            for order_line in customer_master_order_lines:
                master_product_quantity = self.get_total_quantity_after_including_completed_withdrawal(order_line)
                if master_product_quantity > 0:
                    filtered_order_lines.append(order_line)

        filtered_order_lines = list(dict.fromkeys(filtered_order_lines))
        return filtered_order_lines

    def calculate_quantity_for_existing_reports(self, customer_id, product_id, total_received_quantity):
        quantity = total_received_quantity
        order_lines = self.env['amgl.order_line'].search(
            [('customer_id', '=', customer_id), ('products', '=', product_id), ('is_master_records', '=', False),
             ('is_active', '=', True)])
        if order_lines:
            for item in order_lines:
                if item.metal_movement_id and item.metal_movement_id.state != 'completed':
                    quantity += (-item.total_received_quantity)

        return quantity

    def get_total_quantity_after_including_completed_withdrawal(self, order):
        master_product_quantity = order.total_received_quantity
        order_lines = self.env['amgl.order_line'].search(
            [('products', '=', order.products.id), ('is_master_records', '=', False),
             ('customer_id', '=', order.customer_id.id)])
        if order_lines:
            for item in order_lines:
                if item.metal_movement_id and item.metal_movement_id.state != 'completed' and item.metal_movement_id.mmr_number:
                    master_product_quantity += (-item.total_received_quantity)
        return master_product_quantity

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

    def calculate_account_storage_fees(self, account_fees, account_value, custodian_name='', account_type=''):
        _account_type = ''
        if account_type:
            _account_type = account_type
        if 'Gold' in custodian_name:
            account_fees = self.calculate_gold_star_account_storage_fees(account_fees, account_value, _account_type)
        elif 'New Direction' in custodian_name:
            account_fees = self.calculate_new_direction_account_storage_fees(account_fees, account_value, _account_type)
        elif 'Provident Trust' in custodian_name:
            account_fees = self.calculate_provident_trust_account_storage_fees(account_value, _account_type)
        elif 'Equity' in custodian_name:
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
            elif 50000.01 < account_value <= 150000.0:
                outcome_fees = 125.0
            elif 150000.01 < account_value <= 500000.0:
                outcome_fees =  150.0
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

    def calculate_provident_trust_account_storage_fees(self, account_value, account_type=False):
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

    #endregion

    def get_years(self):
        year_list = []
        current_year = int(datetime.datetime.today().year) + 5
        for i in range(2016, current_year):
            year_list.append((str(i), str(i)))
        return year_list

    def get_months(self):
        return [('1', 'January'), ('2', 'February'), ('3', 'March'), ('4', 'April'),
                ('5', 'May'), ('6', 'June'), ('7', 'July'), ('8', 'August'),
                ('9', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December')]

    def create_excel_file(self, start_date, end_date):
        bold, file_name, workbook, worksheet = self.configure_workbook()
        Reports.add_headers(bold, worksheet)
        row_count = 2
        attachment_id = 0
        total_cells_format = workbook.add_format({'bold': True})
        total_cells_format.set_border(1)
        is_data_exists = self.add_rows_in_worksheet(row_count, worksheet, start_date, end_date, workbook)
        workbook.close()
        if is_data_exists:
            attachment = self.add_file_in_attachment(file_name)
            attachment_id = attachment.id
        return attachment_id, file_name

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

    def add_csv_file_in_attachment(self, full_file_name, file_name):
        byte_data = 0
        with open(full_file_name, "rb") as csv:
            byte_data = csv.read()
        attachment = self.env['ir.attachment'].create({'name': file_name,
                                                       'datas': base64.b64encode(byte_data),
                                                       'datas_fname': file_name,
                                                       'res_model': 'res.users',
                                                       'res_id': 1, })
        return attachment

    def add_rows_in_worksheet(self, row_count, worksheet, start_date, end_date, workbook):
        is_data_exists = False
        column_count = 0
        filtered_transactions = self.env['amgl.fees'].search([])
        customers = self.env['amgl.customer'].search([('is_account_closed', '=', False),('custodian_id', '=', self.custodian.id)])
        total_deposit = total_withdrawal = total_shipment = total_administrative = total_other = 0
        format_for_numeric_without_bold = workbook.add_format({'align': 'right'})
        format_for_numeric_bold = workbook.add_format({'bold': True, 'align': 'right', })
        format_for_numeric_bold.set_border(1)
        for customer in customers:
            unique_batches = []
            customer_transactions = []
            for item in filtered_transactions:
                if item.customer_id.id == customer.id:
                    customer_transactions.append(item)
            for transaction in customer_transactions:
                render_row = False
                if transaction.metal_movement_id and transaction.total_fees:
                    metal_movement = self.env['amgl.metal_movement'].search(
                        [('id', '=', transaction.metal_movement_id.id)])
                    date_create = datetime.datetime.strptime(metal_movement.date_create, '%Y-%m-%d')
                    if date_create >= start_date and date_create <= end_date:
                        render_row = True
                    date_create = str(
                        datetime.datetime.strptime(str(transaction.metal_movement_id.date_create), '%Y-%m-%d').strftime(
                            "%m/%d/%Y"))

                if render_row:
                    batch_number = self.get_transaction_reference_number(transaction)
                    if batch_number not in unique_batches:
                        total_deposit += transaction.inbound_fees
                        total_withdrawal += transaction.outbound_fees
                        total_shipment += transaction.shipment_fees
                        total_administrative += transaction.administrative_fees
                        total_other += transaction.other_fees
                        worksheet.write(row_count, column_count, customer.last_name)
                        column_count += 1
                        worksheet.write(row_count, column_count, customer.first_name)
                        column_count += 1
                        worksheet.write(row_count, column_count,
                                        customer.account_number if 'Gold' not in customer.custodian_id.name else customer.gst_account_number)
                        column_count += 1
                        worksheet.write(row_count, column_count, self.get_transaction_reference_number(transaction))
                        column_count += 1
                        worksheet.write(row_count, column_count,
                                        date_create if transaction.metal_movement_id else date_received)
                        column_count += 1
                        worksheet.write(row_count, column_count, '$ ' + str('{0:,.2f}'.format(transaction.inbound_fees)),
                                        format_for_numeric_without_bold)
                        column_count += 1
                        worksheet.write(row_count, column_count, '$ ' + str('{0:,.2f}'.format(transaction.outbound_fees)),
                                        format_for_numeric_without_bold)
                        column_count += 1
                        worksheet.write(row_count, column_count, '$ ' + str('{0:,.2f}'.format(transaction.shipment_fees)),
                                        format_for_numeric_without_bold)
                        column_count += 1
                        worksheet.write(row_count, column_count,
                                        '$ ' + str('{0:,.2f}'.format(transaction.administrative_fees)),
                                        format_for_numeric_without_bold)
                        column_count += 1
                        worksheet.write(row_count, column_count, '$ ' + str('{0:,.2f}'.format(transaction.other_fees)),
                                        format_for_numeric_without_bold)
                        column_count += 1
                        worksheet.write(row_count, column_count,
                                        '$ ' + str('{0:,.2f}'.format(self.get_total_fees(transaction))),
                                        format_for_numeric_without_bold)
                        column_count += 1
                        worksheet.write(row_count, column_count, transaction.fee_note if transaction.fee_note else '')
                        row_count += 1
                        column_count = 0
                        unique_batches.append(batch_number)
        column_count = 5
        worksheet.write(row_count, column_count, '$ ' + str('{0:,.2f}'.format(total_deposit)), format_for_numeric_bold)
        column_count += 1
        worksheet.write(row_count, column_count, '$ ' + str('{0:,.2f}'.format(total_withdrawal)),
                        format_for_numeric_bold)
        column_count += 1
        worksheet.write(row_count, column_count, '$ ' + str('{0:,.2f}'.format(total_shipment)), format_for_numeric_bold)
        column_count += 1
        worksheet.write(row_count, column_count, '$ ' + str('{0:,.2f}'.format(total_administrative)),
                        format_for_numeric_bold)
        column_count += 1
        worksheet.write(row_count, column_count, '$ ' + str('{0:,.2f}'.format(total_other)), format_for_numeric_bold)
        column_count += 1
        worksheet.write(row_count, column_count, '$ ' + str('{0:,.2f}'.format(
            total_deposit + total_other + total_withdrawal + total_shipment + total_administrative)),
                        format_for_numeric_bold)
        is_data_exists = True

        return is_data_exists

    @staticmethod
    def get_total_fees(transaction):
        return transaction.inbound_fees + transaction.outbound_fees + transaction.shipment_fees + transaction.administrative_fees + transaction.other_fees

    def get_transaction_reference_number(self, current_transaction):
        if current_transaction.metal_movement_id:
            return self.env['amgl.metal_movement'].search(
                [('id', '=', current_transaction.metal_movement_id.id)]).mmr_number
        else:
            return self.env['amgl.order_line'].search([(
                'id', '=', current_transaction.order_line_id.id)]).batch_number

    @staticmethod
    def add_headers(bold, worksheet):
        worksheet.write('A1', 'Last Name', bold)
        worksheet.write('B1', 'First Name', bold)
        worksheet.write('C1', 'Account Number', bold)
        worksheet.write('D1', 'Transaction Ref#', bold)
        worksheet.write('E1', 'Transaction Date', bold)
        worksheet.write('F1', 'Deposit Fee', bold)
        worksheet.write('G1', 'Withdrawal Fee', bold)
        worksheet.write('H1', 'Shipping Fee', bold)
        worksheet.write('I1', 'Administrative Fee', bold)
        worksheet.write('J1', 'Other Fee', bold)
        worksheet.write('K1', 'Total Fees', bold)
        worksheet.write('L1', 'Fee Notes', bold)

    @api.onchange('report_types')
    def onchange_report_types(self):
        if self.report_types:
            self.update({
                'report_validation_message': ''
            })
            if 'new_direction_new_accounts_billing_commingled' in self.report_types \
                    or 'new_direction_new_accounts_billing_segregated' in self.report_types \
                    or 'new_direction_existing_accounts_billing_commingled' in self.report_types \
                    or 'new_direction_existing_accounts_billing_segregated' in self.report_types:
                self.update({
                    'show_download_report_button': False,
                    'show_month': False,
                    'show_year': False,
                    'show_download_transaction_invoice': True,
                    'show_report_format': False,
                    'show_customers': True,
                })
                if 'new_accounts' in self.report_types:
                    self.update({
                        'show_bill_customers': False
                    })
                else:
                    self.update({
                        'show_bill_customers': True
                    })
                self.validate_closing_rate_existence()
            elif 'custodian_transaction_report' in self.report_types:
                self.update({
                    'show_month': False,
                    'show_year': False,
                    'show_download_transaction_invoice': False,
                    'show_report_format': False,
                    'show_customers': True,
                    'show_download_report_button': True,
                    'show_bill_customers': True

                })
            elif 'detail_transaction_report' or 'daily_detail_transaction_report' in self.report_types:
                self.update({
                    'show_month': False,
                    'show_year': False,
                    'show_download_report_button': False,
                    'show_customers': True,
                    'show_download_transaction_invoice': True,
                    'show_report_format': False,
                    'show_bill_customers': True

                })
            elif 'custodian_inventory_by_customer' in self.report_types:
                self.update({
                    'show_month': False,
                    'show_year': False,
                    'show_download_report_button': False,
                    'show_customers': True,
                    'show_download_transaction_invoice': True,
                    'show_report_format': False,
                    'show_bill_customers': True

                })
            elif 'physical_inventory' in self.report_types \
                    or 'custodian_inventory_by_customer_segregated' in self.report_types \
                    or 'custodian_inventory_by_customer_commingled' in self.report_types \
                    or 'custodian_inventory_by_product' in self.report_types \
                    or 'custodian_inventory_by_product_segregated' in self.report_types \
                    or 'custodian_inventory_by_product_commingled' in self.report_types:
                self.update({
                    'show_month': True,
                    'show_year': True,
                    'show_download_report_button': False,
                    'show_customers': True,
                    'show_download_transaction_invoice': True,
                    'show_report_format': True,
                    'show_bill_customers': True
                })
            elif 'combined_holding_statement' == self.report_types or \
                    'customer_position_listing' == self.report_types or \
                    'customer_history_by_product' == self.report_types or \
                    'customer_fair_holdings' == self.report_types or \
                    'combined_holding_statement_by_customer' == self.report_types:
                self.update({
                    'show_month': True,
                    'show_year': True,
                    'show_download_transaction_invoice': True,
                    'show_report_format': True,
                    'show_customers': True,
                    'show_bill_customers': True
                })
                if self.custodian:
                    if 'Gold' in self.custodian.name or 'Provident' in self.custodian.name:
                        self.update({'show_download_report_button': False})
                    else:
                        self.update({
                            'report_validation_message': 'Sorry, this report is only available to GoldStar!',
                            'show_download_report_button': True
                        })
                else:
                    self.update({'show_download_report_button': False})

        else:
            self.update({
                'show_month': False,
                'show_year': False,
                'show_download_report_button': False,
                'show_download_transaction_invoice': True,
                'show_customers': True,
                'show_report_format': True,
                'show_bill_customers': True
            })
        if self.report_types:
            self.update({'month': '', 'year': ''})

    def configure_workbook(self):
        file_name = "/excel/" + str(calendar.month_name[int(self.month)]) + ' ' + str(
            self.year) + ' Transaction Invoice.xlsx'
        workbook = xlsxwriter.Workbook(file_name)
        worksheet = workbook.add_worksheet('Transaction Invoice')
        bold = workbook.add_format({'bold': True})
        return bold, file_name, workbook, worksheet

    @staticmethod
    def configure_daily_detail_transaction_csv(self):
        file_name = "/csv/Daily Detail Transaction Invoice.csv"
        workbook = xlsxwriter.Workbook(file_name)
        worksheet = workbook.add_worksheet('Transaction Invoice')
        bold = workbook.add_format({'bold': True})
        return bold, file_name, workbook, worksheet

    @api.onchange('custodian')
    def on_change_custodian(self):
        if self.custodian:
            self.update({'is_custodian_selected': True})
            if self.report_types:
                if 'new_accounts' in self.report_types or 'existing' in self.report_types:
                    self.validate_closing_rate_existence()
                if self.report_types == 'customer_position_listing' or self.report_types == 'customer_fair_holdings' or self.report_types == 'customer_history_by_product' or self.report_types == 'combined_holding_statement' or self.report_types == 'combined_holding_statement_by_customer':
                    if 'Gold' in self.custodian.name or 'Provident' in self.custodian.name:
                        self.update({
                            'report_validation_message': '',
                            'show_download_report_button': False
                        })
                    else:
                        self.update({
                            'report_validation_message': 'Sorry, this report is only available to GoldStar!',
                            'show_download_report_button': True
                        })

            self.env.cr.execute("""
                        SELECT c.id
                        FROM amgl_customer c
                        INNER JOIN amgl_custodian cu ON cu.id = c.custodian_id
                        WHERE c.custodian_id = """ + str(self.custodian.id) + " """)
            customers_ids = self.env.cr.fetchall()
            return {'domain': {'customers': [('id', 'in', customers_ids)]}}

    @api.onchange('month')
    def on_change_month(self):
        if self.report_types and ('new_accounts' in self.report_types or 'existing' in self.report_types):
            self.validate_closing_rate_existence()

    @api.onchange('year')
    def on_change_year(self):
        if self.report_types and ('new_accounts' in self.report_types or 'existing' in self.report_types):
            self.validate_closing_rate_existence()

    def validate_closing_rate_existence(self):
        if self.report_types:
            if self.month and self.year and self.custodian and ('new_accounts' in self.report_types or 'existing' in self.report_types):
                month = str(calendar.month_name[int(self.month)])
                record = self.env['amgl.closing.rates'].search([('month', '=', month), ('years', '=', str(self.year))])
                if not record:
                    raise ValidationError('Closing rate is not provided against selected fields.')

    def get_additional_email_subject_info(self):
        base_url = self.env['ir.config_parameter'].get_param('amgl.live.url')
        subject = ''
        if 'irastorage' not in base_url:
            if 'localhost' in base_url:
                subject = '(Test: Localhost) '
            elif 'odev' in base_url:
                subject = '(Test: Odev) '
        return subject

    def generate_customer_fair_holdings_report(self):
        customers = self.env['amgl.customer'].search(
            [('custodian_id', '=', self.custodian.id),('is_account_closed', '=', False)], order='last_name asc').ids
        report_name = self.fetch_report_name()
        data_object = {
            'ids': customers,
            'model': 'amgl.customer',
            'form': customers
        }
        selected_date = datetime.datetime.now()
        context = dict(self.env.context,
                       selected_date=str(calendar.month_name[selected_date.month]) + ", " + str(selected_date.year),
                       custodian = self.custodian.name)
        return {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': data_object,
            'context': context
        }

    def generate_combined_holding_statement_report(self):
        customers = self.env['amgl.customer'].search([('is_account_closed', '=', False)])
        context = dict(self.env.context, custodian= self.custodian.name)
        data_object = {
            'ids': customers.ids,
            'model': 'amgl.customer',
            'form': customers.ids
        }
        report_name = self.fetch_report_name()
        return {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': data_object
        }

    def fetch_report_name(self):
        report_name = ''
        if self.report_types == 'combined_holding_statement':
            if 'Gold' in self.custodian.name:
                report_name = 'amgl.combined_holding_statement_report_template'
            elif 'Provident' in self.custodian.name:
                report_name = 'amgl.combined_holding_statement_report_template_provident'
        elif self.report_types == 'combined_holding_statement_by_customer':
            if 'Gold' in self.custodian.name:
                report_name = 'amgl.combined_holding_statement_by_customer_report_template'
            elif 'Provident' in self.custodian.name:
                report_name = 'amgl.combined_holding_statement_by_customer_report_template_provident'
        elif self.report_types == 'customer_history_by_product':
            if 'Gold' in self.custodian.name:
                report_name = 'amgl.customer_history_by_product_report_template'
            elif 'Provident' in self.custodian.name:
                report_name = 'amgl.customer_history_by_product_report_template_provident'
        elif self.report_types == 'customer_position_listing':
            if 'Gold' in self.custodian.name:
                report_name = 'amgl.customer_position_listing_report_template'
            elif 'Provident' in self.custodian.name:
                report_name = 'amgl.customer_position_listing_report_template_provident'
        elif self.report_types == 'customer_fair_holdings':
            if 'Gold' in self.custodian.name:
                report_name = 'amgl.customer_fair_holdings_report_template'
            elif 'Provident' in self.custodian.name:
                report_name = 'amgl.customer_fair_holdings_report_template_provident'
        return report_name


    def generate_combined_holding_by_customer_report(self):
        customers = self.env['amgl.customer'].search([('is_account_closed', '=', False)])
        data_object = {
            'ids': customers.ids,
            'model': 'amgl.customer',
            'form': customers.ids
        }
        report_name = self.fetch_report_name()
        return {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': data_object
        }

    # region GoldStar Daily Reports

    def process_goldstar_daily_reports(self):
        template = self.env.ref('amgl.goldstar_daily_reports_email_template', raise_if_not_found=True)
        cplId = self.generate_customer_poistion_listing_report_for_email('Gold').id  # Customer Position Listing Report
        fhrId = self.generate_fair_holding_report_for_email('Gold').id  # FairValue Holding Report
        chsId = self.generate_combined_holding_statement_report_for_email('Gold').id  # Combined Holding Report
        chsByCustomerIid = self.generate_combined_holding_by_customer_report_for_email('Gold').id  # Combined Holding By Customer Report
        chbpId = self.generate_customer_history_by_product_report_for_email('Gold').id  # Customer Holding By Product Report

        self.send_email_if_odev(chbpId, chsByCustomerIid, chsId, cplId, fhrId, template)

    def daily_detailed_transaction_report_for_email(self):

        tz = pytz.timezone('US/Eastern')
        eastern_now = datetime.datetime.now(tz)
        yesterday_date = datetime.datetime.today() - datetime.timedelta(1)
        previous_day = yesterday_date.strftime('%A')

        if previous_day == 'Sunday':
            return True
        if eastern_now.hour == 05 and eastern_now.minute == 30:
            cust_code = 'ETI'
            order_lines = self.env['amgl.order_line'].search(
                [('is_master_records', '=', False), ('is_active', '=', True), ('custodian_code', '=', cust_code),
                 ('date_received', '=', str(yesterday_date))],
                order='transaction_detail_sort_date asc, customer_id')
            filtered_order_line_ids = []

            for item in order_lines:
                item_month = datetime.datetime.strptime(item.transaction_detail_sort_date, '%Y-%m-%d').month
                item_year = datetime.datetime.strptime(item.transaction_detail_sort_date, '%Y-%m-%d').year
                current_month = datetime.datetime.today().month
                current_year = datetime.datetime.today().year
                if item_year == current_year:
                    if item_month == current_month:
                        filtered_order_line_ids.append(item.id)

            report_name = 'amgl.daily_detailed_transaction_report_template'
            data_object = {
                'ids': filtered_order_line_ids,
                'model': 'amgl.order_line',
                'form': filtered_order_line_ids
            }

            report_result = self.env['report'].get_pdf(filtered_order_line_ids, report_name, data=data_object)
            attachment_pdf = self.add_report_to_attachment(report_result, 'Daily Detail Transactioon Report.pdf')
            attachment_csv, file_name = self.generate_daily_details_transaction_report_csv(True)

            self.send_email_for_daily_detail_transaction_report([attachment_pdf.id, attachment_csv.id])

    def send_email_for_daily_detail_transaction_report(self, attachment_ids):
        email_subject = 'Equity Daily Transaction Detail Report'
        email_cc = self.env['ir.config_parameter'].get_param('email.cc')
        emails = self.get_emails_for_daily_detail_report_email_equity()
        template = self.env.ref('amgl.goldstar_daily_reports_email_template', raise_if_not_found=True)
        template.with_context(
            email_subject=email_subject,
            email_to=emails).send_mail(
            1, force_send=False, raise_exception=True,
            email_values={'attachment_ids': attachment_ids}
        )


    def send_email_if_odev(self, chbpId, chsByCustomerIid, chsId, cplId, fhrId, template):
        host_url = self.env['ir.config_parameter'].get_param('amgl.live.url')
        is_request_from_odev = False
        if 'odev' in host_url:
            is_request_from_odev = True
        if is_request_from_odev:
            email_subject = 'AMGL Daily Reports'
            additional_email_subject_info = self.get_additional_email_subject_info()
            if additional_email_subject_info:
                email_subject = additional_email_subject_info + email_subject

            email_cc = self.env['ir.config_parameter'].get_param('email.cc')

            emails = self.get_emails_for_daily_goldstar_report_email('Goldstar')

            template.with_context(
                email_subject=email_subject,
                email_cc=email_cc,
                email_to=emails).send_mail(
                1, force_send=False, raise_exception=True,
                email_values={'attachment_ids': [cplId, chsId, chsByCustomerIid, fhrId, chbpId]}
            )

    def upload_file(self, attachment, report_name, custodian_name):
        host_url = self.env['ir.config_parameter'].get_param('amgl.live.url')
        if 'irastorage' in host_url:
            if 'Gold' in custodian_name:
                directory_name = 'GoldStar Trust Company Reports'
                local_file_path = self.get_local_file_path_according_to_operating_system_and_server(attachment)
                path = "/GoldStar Trust Company Reports/" + str(datetime.datetime.now(pytz.timezone('US/Pacific')).date()) + '/' + report_name
                ipHost = '10.10.0.27'  # change it to sftp.amark.com when running on local.
                usernameLogin = 'goldstarAM'
                passwordLogin = 'h2S3vMe8'
            elif 'Provident' in custodian_name:
                directory_name = 'Provident Trust Group Reports'
                local_file_path = self.get_local_file_path_according_to_operating_system_and_server(attachment)
                path = "/Provident Trust Group Reports/" + str(datetime.datetime.now(pytz.timezone('US/Pacific')).date()) + '/' + report_name
                ipHost = '10.10.0.27'  # change it to sftp.amark.com when running on local.
                usernameLogin = 'ProvidentTrustGroup'
                passwordLogin = 'nWxoF2XQ'
            elif 'Equity' in custodian_name:
                directory_name = 'Equity Institutional Reports'
                local_file_path = self.get_local_file_path_according_to_operating_system_and_server(attachment)
                path = "/Equity Institutional Reports/" + str(datetime.datetime.now(pytz.timezone('US/Pacific')).date()) + '/' + report_name
                ipHost = 'sftp.amark.com'  # change it to sftp.amark.com when running on local.
                usernameLogin = 'EquityInstitutional'
                passwordLogin = 'MgUo7@J@iP1GoikR'

            host_url = self.env['ir.config_parameter'].get_param('amgl.live.url')
            cnopts = pysftp.CnOpts()
            cnopts.hostkeys = None
            with pysftp.Connection(ipHost, username=usernameLogin, password=passwordLogin, cnopts=cnopts) as sftp:
                remotePathWithOutFileName = "/" + directory_name + "/" + str(datetime.datetime.now(pytz.timezone('US/Pacific')).date())
                try:
                    sftp.chdir(remotePathWithOutFileName)  # Test if remote_path exists

                    print directory_name + ' exists on ftp'

                except IOError:

                    print directory_name + ' does not exists on ftp, now creating.'

                    sftp.mkdir(remotePathWithOutFileName)  # Create remote_path

                    print remotePathWithOutFileName + ' created on ftp, now changing directory.'

                    sftp.chdir(remotePathWithOutFileName)

                    print remotePathWithOutFileName + ' is now the active directory on ftp. '
                sftp.put(local_file_path, path)

                print 'Uploading ' + report_name + ' for ' + str(datetime.datetime.now(pytz.timezone('US/Pacific')).date()) + ' done.'

        if 'odev' in host_url:
            directory_name, ipHost, local_file_path, passwordLogin, path, usernameLogin = self.set_credentials_according_to_custodian_for_odev(attachment, custodian_name, report_name)
            cnopts = pysftp.CnOpts()
            cnopts.hostkeys = None

            with pysftp.Connection(ipHost, username=usernameLogin, password=passwordLogin, cnopts=cnopts) as sftp:

                self.create_directory_if_doesnot_exist_and_change_directory(sftp, directory_name)
                print 'Now going to upload file'
                sftp.put(local_file_path, path)
            print 'Uploading ' + report_name + ' for odev for ' + str(datetime.datetime.now(pytz.timezone('US/Pacific')).date()) + ' done.'

        if 'localhost' in host_url:
            directory_name, ipHost, local_file_path, passwordLogin, path, usernameLogin = self.set_credentials_according_to_custodian_for_dev_testing(attachment, custodian_name, report_name)
            cnopts = pysftp.CnOpts()
            cnopts.hostkeys = None

            with pysftp.Connection(ipHost, username=usernameLogin, password=passwordLogin, cnopts=cnopts) as sftp:

                self.create_directory_if_doesnot_exist_and_change_directory(sftp, directory_name)
                print 'Now going to upload file'
                sftp.put(local_file_path, path)
            print 'Uploading ' + report_name + ' for localhost for ' + str(datetime.datetime.now(pytz.timezone('US/Pacific')).date()) + ' done.'

    def set_credentials_according_to_custodian(self, attachment, custodian_name, report_name):
        if 'Gold' in custodian_name:
            directory_name = 'GoldStar Reports'
            local_file_path = self.get_local_file_path_according_to_operating_system_and_server(attachment)
            path = "/GoldStar Reports/" + str(datetime.datetime.now(pytz.timezone('US/Pacific')).date()) + '/' + report_name
            ipHost = '10.10.0.27'  # change it to sftp.amark.com when running on local.
            usernameLogin = 'goldstarAM'
            passwordLogin = 'h2S3vMe8'
        elif 'Provident' in custodian_name:
            directory_name = 'Provident Trust Group Reports'
            local_file_path = self.get_local_file_path_according_to_operating_system_and_server(attachment)
            path = "/Provident Trust Group Reports/" + str(datetime.datetime.now(pytz.timezone('US/Pacific')).date()) + '/' + report_name
            ipHost = '10.10.0.27'  # change it to sftp.amark.com when running on local.
            usernameLogin = 'ProvidentTrustGroup'
            passwordLogin = 'nWxoF2XQ'
        return directory_name, ipHost, local_file_path, passwordLogin, path, usernameLogin

    def set_credentials_according_to_custodian_for_odev(self, attachment, custodian_name, report_name):
        if 'Gold' in custodian_name:
            directory_name = 'GoldStar Odev Reports'
            local_file_path = self.get_local_file_path_according_to_operating_system_and_server(attachment)
            path = "/GoldStar Odev Reports/" + str(datetime.datetime.now(pytz.timezone('US/Pacific')).date()) + '/' + report_name
            ipHost = '10.10.0.27'  # change it to sftp.amark.com when running on local.
            usernameLogin = 'goldstarAM'
            passwordLogin = 'h2S3vMe8'
        elif 'Provident' in custodian_name:
            directory_name = 'Provident Trust Group Odev Reports'
            local_file_path = self.get_local_file_path_according_to_operating_system_and_server(attachment)
            path = "/Provident Trust Group Odev Reports/" + str(datetime.datetime.now(pytz.timezone('US/Pacific')).date()) + '/' + report_name
            ipHost = '10.10.0.27'  # change it to sftp.amark.com when running on local.
            usernameLogin = 'ProvidentTrustGroup'
            passwordLogin = 'nWxoF2XQ'
        return directory_name, ipHost, local_file_path, passwordLogin, path, usernameLogin

    def set_credentials_according_to_custodian_for_dev_testing(self, attachment, custodian_name, report_name):
        if 'Gold' in custodian_name:
            directory_name = 'GoldStar Dev Testing Reports'
            local_file_path = self.get_local_file_path_according_to_operating_system_and_server(attachment)
            path = "/GoldStar Dev Testing Reports/" + str(datetime.datetime.now(pytz.timezone('US/Pacific')).date()) + '/' + report_name
            ipHost = 'sftp.amark.com'  # change it to sftp.amark.com when running on local.
            usernameLogin = 'goldstarAM'
            passwordLogin = 'h2S3vMe8'
        elif 'Provident' in custodian_name:
            directory_name = 'Provident Trust Group Dev Testing Reports'
            local_file_path = self.get_local_file_path_according_to_operating_system_and_server(attachment)
            path = "/Provident Trust Group Dev Testing Reports/" + str(datetime.datetime.now(pytz.timezone('US/Pacific')).date()) + '/' + report_name
            ipHost = 'sftp.amark.com'  # change it to sftp.amark.com when running on local.
            usernameLogin = 'ProvidentTrustGroup'
            passwordLogin = 'nWxoF2XQ'
        return directory_name, ipHost, local_file_path, passwordLogin, path, usernameLogin

    def is_request_local(self):
        host_url = self.env['ir.config_parameter'].get_param('amgl.live.url')
        is_request_from_localhost = False
        if 'localhost' in host_url:
            is_request_from_localhost = True
        return is_request_from_localhost

    @staticmethod
    def create_directory_if_doesnot_exist_and_change_directory(sftp, directory_name):

        remotePathWithOutFileName = "/" + directory_name + "/" + str(datetime.datetime.now(pytz.timezone('US/Pacific')).date())

        try:
            sftp.chdir(remotePathWithOutFileName)  # Test if remote_path exists

            print directory_name + ' exists on ftp'

        except IOError:

            print directory_name + ' does not exists on ftp, now creating.'

            sftp.mkdir(remotePathWithOutFileName)  # Create remote_path

            print remotePathWithOutFileName + ' created on ftp, now changing directory.'

            sftp.chdir(remotePathWithOutFileName)

            print remotePathWithOutFileName + ' is now the active directory on ftp. '


    def get_local_file_path_according_to_operating_system_and_server(self, attachment):

        is_request_from_localhost = self.is_request_local()

        if platform.system() == 'Linux':
            if is_request_from_localhost:
                localpath = '/home/ahsan/.local/share/Odoo/filestore/' + self._cr.dbname + '/'
            else:
                localpath = '/opt/odoo/.local/share/Odoo/filestore/' + self._cr.dbname + '/'
        else:
            localpath = 'C:/Users/ahsana/AppData/Local/OpenERP S.A/Odoo/filestore/' + self._cr.dbname + '/'

        localpath = localpath + attachment.store_fname

        return localpath

    def generate_fair_holding_report_for_email(self, custodian_keyword):
        custodian = self.env['amgl.custodian'].search([('name', 'ilike', custodian_keyword)])
        customers = self.env['amgl.customer'].search([('custodian_id', '=', custodian.id), ('is_account_closed', '=', False)])
        data_object = {
            'ids': customers.ids,
            'model': 'amgl.customer',
            'form': customers.ids
        }

        if 'Gold' in custodian.name:
            template_name = 'amgl.customer_fair_holdings_report_template'
        if 'Provident' in custodian.name:
            template_name = 'amgl.customer_fair_holdings_report_template_provident'
        report_result = self.env['report'].get_pdf(customers.ids, template_name, data=data_object)
        attachment_id = self.add_report_to_attachment(report_result, 'Customer Fair Value Holdings Report.pdf')
        self.upload_file(attachment_id, 'Customer Fair Value Holdings Report.pdf', custodian.name)
        return attachment_id


    def generate_customer_history_by_product_report_for_email(self, custodian_keyword):
        custodian = self.env['amgl.custodian'].search([('name', 'ilike', custodian_keyword)])
        customers = self.env['amgl.customer'].search([('custodian_id', '=', custodian.id), ('is_account_closed', '=', False)])
        data_object = {
            'ids': customers.ids,
            'model': 'amgl.customer',
            'form': customers.ids
        }
        if 'Gold' in custodian.name:
            template_name = 'amgl.customer_history_by_product_report_template'
        if 'Provident' in custodian.name:
            template_name = 'amgl.customer_history_by_product_report_template_provident'
        report_result = self.env['report'].get_pdf(customers.ids, template_name, data=data_object)
        attachment_id = self.add_report_to_attachment(report_result, 'Customer History By Product.pdf')
        self.upload_file(attachment_id, 'Customer History By Product.pdf', custodian.name)
        return attachment_id


    def generate_customer_poistion_listing_report_for_email(self, custodian_keyword):
        custodian = self.env['amgl.custodian'].search([('name', 'ilike', custodian_keyword)])
        customers = self.env['amgl.customer'].search([('custodian_id', '=', custodian.id), ('is_account_closed', '=', False)])
        data_object = {
            'ids': customers.ids,
            'model': 'amgl.customer',
            'form': customers.ids
        }
        if 'Gold' in custodian.name:
            template_name = 'amgl.customer_position_listing_report_template'
        if 'Provident' in custodian.name:
            template_name = 'amgl.customer_position_listing_report_template_provident'
        report_result = self.env['report'].get_pdf(customers.ids, template_name, data=data_object)
        attachment_id = self.add_report_to_attachment(report_result, 'Customer Position Listing.pdf')
        self.upload_file(attachment_id, 'Customer Position Listing.pdf', custodian.name)
        return attachment_id

    def generate_combined_holding_statement_report_for_email(self, custodian_keyword):
        custodian = self.env['amgl.custodian'].search([('name', 'ilike', custodian_keyword)])
        customers = self.env['amgl.customer'].search([('custodian_id', '=', custodian.id), ('is_account_closed', '=', False)])
        data_object = {
            'ids': customers.ids,
            'model': 'amgl.customer',
            'form': customers.ids
        }
        if 'Gold' in custodian.name:
            template_name = 'amgl.combined_holding_statement_report_template'
        if 'Provident' in custodian.name:
            template_name = 'amgl.combined_holding_statement_report_template_provident'
        report_result = self.env['report'].get_pdf(customers.ids, template_name, data=data_object)
        attachment_id = self.add_report_to_attachment(report_result, 'Combined Holding Statement.pdf')
        self.upload_file(attachment_id, 'Combined Holding Statement.pdf', custodian.name)
        return attachment_id

    def generate_combined_holding_by_customer_report_for_email(self, custodian_keyword):
        custodian = self.env['amgl.custodian'].search([('name', 'ilike', custodian_keyword)])
        customers = self.env['amgl.customer'].search([('custodian_id', '=', custodian.id), ('is_account_closed', '=', False)])
        data_object = {
            'ids': customers.ids,
            'model': 'amgl.customer',
            'form': customers.ids
        }
        template_name = ''
        if 'Gold' in custodian.name:
            template_name = 'amgl.combined_holding_statement_by_customer_report_template'
        if 'Provident' in custodian.name:
            template_name = 'amgl.combined_holding_statement_by_customer_report_template_provident'
        report_result = self.env['report'].get_pdf(customers.ids, template_name, data=data_object)
        attachment_id = self.add_report_to_attachment(report_result, 'Combined Holding Statement By Customer.pdf')
        self.upload_file(attachment_id, 'Combined Holding Statement By Customer.pdf', custodian.name)
        return attachment_id

    def get_emails_for_daily_detail_report_email_equity(self):
        email_groups = self.env['amgl.email.group'].search([])
        emails = ''
        for item in email_groups:
            if 'Equity' in item.name:  # send emails to custodian group
                emails += ',' + item.emails

        emails = emails.lstrip(",")
        emails = emails.rstrip(",")
        return emails

    def get_emails_for_daily_goldstar_report_email(self, cust_name):
        email_groups = self.env['amgl.email.group'].search([])
        emails = ''
        for item in email_groups:
            if cust_name in item.name:  # send emails to custodian group
                emails += ',' + item.emails

        emails = emails.lstrip(",")
        emails = emails.rstrip(",")
        return emails

    # endregion

    # region GTC Transaction History Excel

    def upload_transaction_history_report(self):
        file_name = 'GoldStar Transaction History.csv'
        custodian = self.env['amgl.custodian'].search([('name', 'ilike', 'Gold')])
        all_customers = self.env['amgl.customer'].search(
            [('custodian_id', '=', custodian.id), ('is_account_closed', '=', False)])
        if all_customers:
            file_name_with_dir = self.get_local_file_path_according_to_operating_system_and_server_for_csv() + 'GoldStar Transaction History.csv'
            with open(file_name_with_dir, 'wb') as f:
                for customer in all_customers:
                    all_order_lines = self.env['amgl.order_line'].search(
                        [('customer_id', '=', customer.id), ('is_active', '!=', False), ('is_master_records', '=', False)])
                    for order in all_order_lines:
                        if not order.metal_movement_id or (order.metal_movement_id.id > 0 and order.metal_movement_id.state == 'completed'):
                            row = customer.gst_account_number + ','
                            row += customer.first_name + ' ' + customer.last_name + ','
                            row += customer.gst_account_number + ','
                            row += datetime.datetime.strptime(order.date_received, '%Y-%m-%d').strftime("%m/%d/%Y") + ',' if not order.metal_movement_id.id > 0 else datetime.datetime.strptime(order.metal_movement_id.date_create, '%Y-%m-%d').strftime("%m/%d/%Y") + ','
                            row += order.batch_number + ',' if not order.metal_movement_id.id > 0 else order.metal_movement_id.mmr_number + ','
                            row += 'PS,' if order.metal_movement_id else 'PR,'
                            row += order.products.gs_product_code + ','
                            row += str(order.total_received_quantity) + ','
                            row += 'AMGL,'
                            row += 'GTC,'
                            f.write(row)
                            f.write('\n')
            attachment = self.add_file_in_attachment_history_report(file_name_with_dir)
            self.upload_file(attachment, file_name, custodian.name)

    def upload_transaction_history_report_excel(self):
        file_name = 'GoldStar Transaction History.xlsx'
        bold, red_text, underline, workbook, worksheet = self.configure_workbook_for_transaction_excel_report(file_name)
        right_align = workbook.add_format({'align': 'right'})
        red_text_right_align = workbook.add_format({'font_color': 'red', 'align': 'right'})
        row_count = 0
        column_count = 0
        custodian = self.env['amgl.custodian'].search([('name', 'ilike', 'Gold')])
        all_customers = self.env['amgl.customer'].search([('custodian_id', '=', custodian.id), ('is_account_closed', '=', False)])
        for customer in all_customers:
            all_order_lines = self.env['amgl.order_line'].search(
                [('customer_id', '=', customer.id), ('is_active', '!=', False), ('is_master_records', '=', False)])
            total_weight = 0
            for order in all_order_lines:
                total_weight += order.temp_received_weight
                if order.metal_movement_id:
                    if order.metal_movement_id.state == 'completed':
                        self.add_withdraw_line_history_report(column_count, customer, order, red_text, row_count, worksheet,
                                               red_text_right_align)
                        row_count += 1
                        column_count = 0
                else:
                    self.add_deposit_line_history_report(column_count, customer, order, row_count, worksheet, right_align)
                    row_count += 1
                    column_count = 0
        workbook.close()
        attachment = self.add_file_in_attachment_history_report(file_name)
        self.upload_file(attachment, file_name, custodian.name)


    def configure_workbook_for_transaction_excel_report(self, file_name):
        workbook = xlsxwriter.Workbook(file_name)
        worksheet = workbook.add_worksheet('GTC Inventory')
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

    @staticmethod
    def add_deposit_line_history_report(column_count, customer, order, row_count, worksheet, right_align):
        worksheet.write(row_count, column_count, customer.gst_account_number)
        column_count += 1
        worksheet.write(row_count, column_count, customer.first_name + ' ' + customer.last_name)
        column_count += 1
        worksheet.write(row_count, column_count, customer.gst_account_number)
        column_count += 1
        worksheet.write(row_count, column_count, datetime.datetime.strptime(order.date_received, '%Y-%m-%d').strftime("%m/%d/%Y"))
        column_count += 1
        worksheet.write(row_count, column_count, order.batch_number)
        column_count += 1
        worksheet.write(row_count, column_count, 'PR')
        column_count += 1
        worksheet.write(row_count, column_count, order.products.gs_product_code)
        column_count += 1
        worksheet.write(row_count, column_count, order.total_received_quantity)
        column_count += 1
        worksheet.write(row_count, column_count, 'AMGL')
        column_count += 1
        worksheet.write(row_count, column_count, 'GTC')

    @staticmethod
    def add_withdraw_line_history_report(column_count, customer, order, red_text, row_count, worksheet, red_text_right_align):

        worksheet.write(row_count, column_count, customer.gst_account_number, red_text)
        column_count += 1
        worksheet.write(row_count, column_count, customer.first_name + ' ' + customer.last_name, red_text)
        column_count += 1
        worksheet.write(row_count, column_count, customer.gst_account_number, red_text)
        column_count += 1
        worksheet.write(row_count, column_count, datetime.datetime.strptime(order.metal_movement_id.date_create, '%Y-%m-%d').strftime("%m/%d/%Y"), red_text)
        column_count += 1
        worksheet.write(row_count, column_count, order.metal_movement_id.mmr_number , red_text)
        column_count += 1
        worksheet.write(row_count, column_count, 'PS', red_text)
        column_count += 1
        worksheet.write(row_count, column_count, order.products.gs_product_code, red_text)
        column_count += 1
        worksheet.write(row_count, column_count, order.total_received_quantity, red_text)
        column_count += 1
        worksheet.write(row_count, column_count, 'AMGL', red_text)
        column_count += 1
        worksheet.write(row_count, column_count, 'GTC', red_text)
        column_count += 1

    def add_file_in_attachment_history_report(self, file_name):
        byte_data = 0
        with open(file_name, "rb") as csvfile:
            byte_data = csvfile.read()
        attachment = self.env['ir.attachment'].create({'name': file_name,
                                                       'datas': byte_data.encode('base64'),
                                                       'datas_fname': file_name,
                                                       'res_model': 'res.users',
                                                       'res_id': 1, })
        return attachment

    # endregion

    def get_local_file_path_according_to_operating_system_and_server_for_csv(self):

        is_request_from_localhost = self.is_request_local()

        if platform.system() == 'Linux':
            if is_request_from_localhost:
                localpath = '/home/ahsan/.local/share/Odoo/filestore/' + self._cr.dbname + '/'
            else:
                localpath = '/opt/odoo/.local/share/Odoo/filestore/' + self._cr.dbname + '/'
        else:
            localpath = 'C:/Users/ahsana/AppData/Local/OpenERP S.A/Odoo/filestore/' + self._cr.dbname + '/'

        return localpath

    #region Provident Trust Group Daily Reports

    def process_provident_group_daily_reports(self):
        template = self.env.ref('amgl.goldstar_daily_reports_email_template', raise_if_not_found=True)
        cplId = self.generate_customer_poistion_listing_report_for_email('Provident').id  # Customer Position Listing Report
        chsId = self.generate_combined_holding_statement_report_for_email('Provident').id  # Combined Holding Report
        chsByCustomerIid = self.generate_combined_holding_by_customer_report_for_email('Provident').id  # Combined Holding By Customer Report
        chbpId = self.generate_customer_history_by_product_report_for_email('Provident').id  # Customer Holding By Product Report
        fhrId = self.generate_fair_holding_report_for_email('Provident').id  # FairValue Holding Report

    def upload_transaction_history_report_provident(self):
        file_name = 'Provident Transaction History.csv'
        custodian = self.env['amgl.custodian'].search([('name', 'ilike', 'provident')])
        all_customers = self.env['amgl.customer'].search(
            [('custodian_id', '=', custodian.id), ('is_account_closed', '=', False)])
        if all_customers:
            file_name_with_dir = self.get_local_file_path_according_to_operating_system_and_server_for_csv() + 'Provident Transaction History.csv'
            with open(file_name_with_dir, 'wb') as f:
                for customer in all_customers:
                    all_order_lines = self.env['amgl.order_line'].search(
                        [('customer_id', '=', customer.id), ('is_active', '!=', False), ('is_master_records', '=', False)])
                    for order in all_order_lines:
                        if not order.metal_movement_id or (order.metal_movement_id.id > 0 and order.metal_movement_id.state == 'completed'):
                            row = customer.account_number + ','
                            row += customer.first_name + ' ' + customer.last_name + ','
                            row += customer.account_number + ','
                            row += datetime.datetime.strptime(order.date_received, '%Y-%m-%d').strftime("%m/%d/%Y") + ',' if not order.metal_movement_id.id > 0 else datetime.datetime.strptime(order.metal_movement_id.date_create, '%Y-%m-%d').strftime("%m/%d/%Y") + ','
                            row += order.batch_number + ',' if not order.metal_movement_id.id > 0 else order.metal_movement_id.mmr_number + ','
                            row += 'PS,' if order.metal_movement_id else 'PR,'
                            row += order.products.gs_product_code + ','
                            row += str(order.total_received_quantity) + ','
                            row += 'AMGL,'
                            row += 'GTC,'
                            f.write(row)
                            f.write('\n')
            attachment = self.add_file_in_attachment_history_report(file_name_with_dir)
            self.upload_file(attachment, file_name, custodian.name)

    def upload_equity_daily_transaction_report(self):
        custodian = self.env['amgl.custodian'].search([('name', 'ilike', 'equity')])
        attachment, file_name = self.generate_daily_details_transaction_report_csv(True)
        self.upload_file(attachment, file_name, custodian.name)

    def send_email_equity_daily_detail_transaction_report(self):
        self.daily_detailed_transaction_report_for_email()

    #endregion

    name = fields.Char()
    custodian = fields.Many2one('amgl.custodian', string='Custodian', required=True)
    report_types = fields.Selection(selection=[
        ('new_direction_new_accounts_billing_commingled', 'New Accounts Commingled Storage Invoice'),
        ('new_direction_new_accounts_billing_segregated', 'New Accounts Segregated Storage Invoice'),
        ('new_direction_existing_accounts_billing_commingled','Existing Accounts Commingled Storage Invoice'),
        ('new_direction_existing_accounts_billing_segregated', 'Existing Accounts Segregated Storage Invoice'),
        ('custodian_transaction_report', 'Transaction Invoice'),
        ('detail_transaction_report', 'Detail Transaction Report'),
        ('daily_detail_transaction_report', 'Daily Detail Transaction Report'),
        ('physical_inventory', 'Physical Inventory Summary'),
        ('custodian_inventory_by_customer', 'Custodian Inventory By Customer (Full)'),
        ('custodian_inventory_by_customer_segregated', 'Custodian Inventory By Customer (Segregated)'),
        ('custodian_inventory_by_customer_commingled', 'Custodian Inventory By Customer (Commingled)'),
        ('custodian_inventory_by_product', 'Custodian Inventory By Product (Full)'),
        ('custodian_inventory_by_product_segregated', 'Custodian Inventory By Product (Segregated)'),
        ('custodian_inventory_by_product_commingled', 'Custodian Inventory By Product (Commingled)'),
        ('combined_holding_statement', 'Combined Holding Statement (Full)'),
        ('combined_holding_statement_by_customer', 'Combined Holding Statement By Customer'),
        ('customer_position_listing', 'Customer Position Listing'),
        ('customer_history_by_product', 'Customer History By Product'),
        ('customer_fair_holdings', 'Customer Fair Value Holdings'),
    ], required=True)
    report_format = fields.Selection(selection=[('pdf', 'PDF'), ('excel', 'Excel'), ('csv', 'CSV')])
    customers = fields.Many2one('amgl.customer', string='Customers')
    month = fields.Selection(selection=get_months, string='Month')
    year = fields.Selection(selection=get_years, string='Year')
    show_month = fields.Boolean(default=False)
    show_year = fields.Boolean(default=False)
    show_download_report_button = fields.Boolean(default=False)
    show_download_transaction_invoice = fields.Boolean(default=False)
    show_customers = fields.Boolean(default=False)
    show_report_format = fields.Boolean(default=False)
    show_bill_customers = fields.Boolean(default=False)
    report_validation_message = fields.Char(store=False)
    is_custodian_selected = fields.Boolean(default=False)
    bill_customers = fields.Boolean(default=False)