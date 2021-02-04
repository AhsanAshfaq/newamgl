# -*- coding: utf-8 -*-

import base64
import calendar
import datetime
import xlsxwriter
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CustodianReports(models.Model):
    _name = 'amgl.custodian_reports'
    _description = 'Custodian Reports'

    gold_price = 0
    silver_price = 0
    platinum_price = 0
    palladium_price = 0

    def fetch_reports(self):

        if 'current_inventory_excel' in self.report_types or 'customer_metal_activity_excel' in self.report_types:
            if not self.customers:
                raise ValidationError('Please select customer if you are trying to fetch customer specific report.')
            if 'customer_metal_activity_excel' in self.report_types:
                attachment_id, file_name = self.create_excel_for_customer_metal_activity()
            elif 'current_inventory_excel' in self.report_types:
                attachment_id, file_name = self.create_excel_for_current_inventory()
            base_url = self.env['ir.config_parameter'].get_param('amgl.live.url')
            return {
                'type': 'ir.actions.act_url',
                'url': base_url + '/web/content/%s/%s' % (attachment_id, file_name.replace('/excel/', '')),
                'target': 'current',
            }
        if 'current_inventory_pdf' in self.report_types or 'customer_metal_activity_pdf' in self.report_types:
            if not self.customers:
                raise ValidationError('Please select customer if you are trying to fetch customer specific report.')
            report_name = ''
            if 'current_inventory_pdf' in self.report_types:
                report_name = 'amgl.report_customer_current_inventory'
            else:
                report_name = 'amgl.report_customer_metal_activity'

            data_object = {
                'ids': self.customers.ids,
                'model': 'amgl.customer',
                'form': self.customers.ids
            }
            return {
                'type': 'ir.actions.report.xml',
                'report_name': report_name,
                'datas': data_object
            }

        if 'custodian_inventory_by_customer' in self.report_types:
            customers = []
            if 'custodian_inventory_by_customer_segregated' == self.report_types:
                customers = self.env['amgl.customer'].search([('custodian_id','=', self.custodian_id.id), ('account_type','=', 'Segregated')], order='last_name asc').ids
            if 'custodian_inventory_by_customer_commingled' == self.report_types:
                customers = self.env['amgl.customer'].search([('custodian_id','=', self.custodian_id.id), ('account_type','=', 'Commingled')], order='last_name asc').ids
            if 'custodian_inventory_by_customer' == self.report_types:
                customers = self.env['amgl.customer'].search([('custodian_id','=', self.custodian_id.id)], order='last_name asc').ids

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

    def reload(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    @api.onchange('report_types')
    def onchange_report_types(self):
        if self.report_types:
            if 'current_inventory' in self.report_types or 'customer_metal_activity' in self.report_types:
                self.update({
                    'show_customers': False,
                    'show_download_report_button': False,
                })
            elif 'custodian_inventory_by_customer' in self.report_types\
                    or 'custodian_inventory_by_customer_segregated' in self.report_types\
                    or 'custodian_inventory_by_customer_commingled' in self.report_types:
                self.update({
                    'show_download_report_button': False,
                    'show_customers': True
                })

        else:
            self.update({
                'show_download_report_button': False,
                'show_customers': False,
            })

    @api.onchange('custodian_id')
    def on_change_custodian(self):
        if self.custodian_id:
            self.env.cr.execute("""
                        SELECT c.id
                        FROM amgl_customer c
                        INNER JOIN amgl_custodian cu ON cu.id = c.custodian_id
                        WHERE c.custodian_id = """ + str(self.custodian_id.id) + " """)
            customers_ids = self.env.cr.fetchall()
            return {'domain': {'customers': [('id', 'in', customers_ids)]}}

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

    def create_excel_for_customer_metal_activity(self):
        bold, file_name, workbook, worksheet = self.configure_workbook_for_customer_metal_activity()
        CustodianReports.add_headers_for_customer_metal_activity(bold, worksheet, workbook)
        attachment_id = 0
        total_cells_format = workbook.add_format({'bold': True})
        total_cells_format.set_border(1)
        is_data_exists = self.add_rows_in_worksheet_for_customer_metal_activity(worksheet, bold, workbook)
        workbook.close()
        if is_data_exists:
            attachment = self.add_file_in_attachment(file_name)
            attachment_id = attachment.id
        return attachment_id, file_name

    def create_excel_for_current_inventory(self):
        bold, file_name, workbook, worksheet = self.configure_workbook_for_currrent_inventory()
        CustodianReports.add_headers_for_current_inventory(bold, worksheet, workbook)
        attachment_id = 0
        total_cells_format = workbook.add_format({'bold': True})
        total_cells_format.set_border(1)
        is_data_exists = self.add_rows_in_worksheet_for_current_inventory(worksheet, bold, workbook)
        workbook.close()
        if is_data_exists:
            attachment = self.add_file_in_attachment(file_name)
            attachment_id = attachment.id
        return attachment_id, file_name

    def configure_workbook_for_customer_metal_activity(self):
        file_name = "/excel/" + self.customers.full_name + ' Metal Activity.xlsx'
        workbook = xlsxwriter.Workbook(file_name)
        worksheet = workbook.add_worksheet('Customer Metal Activity')
        bold = workbook.add_format({'bold': True})
        return bold, file_name, workbook, worksheet

    def configure_workbook_for_currrent_inventory(self):
        file_name = "/excel/" + 'Current Inventory For ' + self.customers.full_name + '.xlsx'
        workbook = xlsxwriter.Workbook(file_name)
        worksheet = workbook.add_worksheet('Current Inventory')
        bold = workbook.add_format({'bold': True})
        return bold, file_name, workbook, worksheet

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

    @staticmethod
    def add_headers_for_customer_metal_activity(bold, worksheet, workbook):
        row_count = 10
        column_count = 0
        format_for_title = workbook.add_format({'bold': True,'align': 'center','valign': 'vcenter'})
        format_for_date = workbook.add_format({'bold': True, 'align': 'right', 'valign': 'vcenter'})
        worksheet.merge_range(0, 0, 1, 6, 'Customer Metal Activity', format_for_title)
        worksheet.merge_range(2, 5, 2, 6, str(datetime.datetime.strptime(str(datetime.datetime.now().date()), '%Y-%m-%d').strftime("%m/%d/%Y")), format_for_date)
        worksheet.write(row_count, column_count, 'Product', bold)
        worksheet.write(row_count, column_count + 1, 'Commodity', bold)
        worksheet.write(row_count, column_count + 2, 'Quantity', bold)
        worksheet.write(row_count, column_count + 3, 'Total Weight', bold)
        worksheet.write(row_count, column_count + 4, 'Date', bold)

    @staticmethod
    def add_headers_for_current_inventory(bold, worksheet, workbook):
        row_count = 10
        column_count = 0
        format_for_title = workbook.add_format({ 'bold': True, 'align': 'center', 'valign': 'vcenter' })
        format_for_date = workbook.add_format({'bold': True,'align': 'right','valign': 'vcenter'})
        worksheet.merge_range(0, 0, 1, 6, 'Customer Current Inventory', format_for_title)
        worksheet.merge_range(3, 5, 3, 6, str(datetime.datetime.strptime(str(datetime.datetime.now().date()), '%Y-%m-%d').strftime("%m/%d/%Y")), format_for_date)
        worksheet.write(row_count, column_count, 'Product', bold)
        worksheet.write(row_count, column_count + 1, 'Commodity', bold)
        worksheet.write(row_count, column_count + 2, 'Quantity', bold)
        worksheet.write(row_count, column_count + 3, 'Total Weight', bold)

    def add_rows_in_worksheet_for_customer_metal_activity(self, worksheet, bold, workbook):
        is_data_exists = False
        format_for_numeric_bold = workbook.add_format({'bold': True, 'align': 'right', })
        format_for_numeric_without_bold = workbook.add_format({'align': 'right'})
        customer_current_activity = self.env['amgl.order_line'].search(
            [('customer_id', '=', self.customers.id),('is_master_records', '=', False)])
        row_count = 5
        column_count = 0
        worksheet.write(row_count, column_count, 'First Name', bold)
        worksheet.write(row_count, column_count + 1, self.customers.first_name)
        worksheet.write(row_count, column_count + 5, 'Last Name', bold)
        worksheet.write(row_count, column_count + 6, self.customers.last_name)
        row_count += 1
        worksheet.write(row_count, column_count, 'Account Type', bold)
        worksheet.write(row_count, column_count + 1, self.customers.account_type)
        worksheet.write(row_count, column_count + 5, 'Account Number', bold)
        worksheet.write(row_count, column_count + 6,
                        self.customers.account_number if 'Gold' not in self.customers.custodian_id.name else self.customers.gst_account_number)
        row_count += 1
        worksheet.write(row_count, column_count, 'Custodian', bold)
        worksheet.write(row_count, column_count + 1, self.customers.custodian_id.name)
        row_count = 11
        column_count = 0
        if customer_current_activity:
            for inventory in customer_current_activity:
                worksheet.write(row_count, column_count, inventory.products.goldstar_name)
                column_count += 1
                worksheet.write(row_count, column_count, inventory.commodity)
                column_count += 1
                worksheet.write(row_count, column_count, str('{0:,.0f}'.format(inventory.total_received_quantity)),format_for_numeric_without_bold)
                column_count += 1
                worksheet.write(row_count, column_count, str('{0:,.2f}'.format(inventory.temp_received_weight) + ' oz'),
                                format_for_numeric_without_bold)
                column_count += 1
                worksheet.write(row_count, column_count,str(datetime.datetime.strptime(inventory.date_for_customer_metal_activitiy, '%Y-%m-%d').strftime("%m/%d/%Y")))
                column_count += 1
                is_data_exists = True
                row_count += 1
                column_count = 0
        else:
            worksheet.write(row_count, column_count, 'N/A')
            column_count += 1
            worksheet.write(row_count, column_count, 'N/A')
            column_count += 1
            worksheet.write(row_count, column_count, str('{0:,.0f}'.format(0)),
                            format_for_numeric_without_bold)
            column_count += 1
            worksheet.write(row_count, column_count, str('{0:,.2f}'.format(0) + ' oz'),
                            format_for_numeric_without_bold)
            column_count += 1
            worksheet.write(row_count, column_count, 'N/A')
            column_count += 1
            is_data_exists = True
            row_count += 1
        self.add_total_table(row_count, worksheet, bold, format_for_numeric_bold, format_for_numeric_without_bold)

        return is_data_exists

    def add_rows_in_worksheet_for_current_inventory(self, worksheet, bold, workbook):
        is_data_exists = False
        format_for_numeric_bold = workbook.add_format({'bold': True, 'align': 'right', })
        format_for_numeric_without_bold = workbook.add_format({'align': 'right'})
        customer_current_activity = self.env['amgl.order_line'].search(
            [('is_master_records', '=', True), ('is_active', '=', True),
             ('customer_id', '=', self.customers.id), ('total_received_quantity', '>', 0)])
        row_count = 5
        column_count = 0
        worksheet.write(row_count, column_count, 'First Name', bold)
        worksheet.write(row_count, column_count + 1, self.customers.first_name)
        worksheet.write(row_count, column_count + 5, 'Last Name', bold)
        worksheet.write(row_count, column_count + 6, self.customers.last_name)
        row_count += 1
        worksheet.write(row_count, column_count, 'Account Type', bold)
        worksheet.write(row_count, column_count + 1, self.customers.account_type)
        worksheet.write(row_count, column_count + 5, 'Account Number', bold)
        worksheet.write(row_count, column_count + 6,
                        self.customers.account_number if 'Gold' not in self.customers.custodian_id.name else self.customers.gst_account_number)
        row_count += 1
        worksheet.write(row_count, column_count, 'Custodian', bold)
        worksheet.write(row_count, column_count + 1, self.customers.custodian_id.name)
        row_count = 11
        column_count = 0
        if customer_current_activity:
            for inventory in customer_current_activity:
                worksheet.write(row_count, column_count, inventory.products.goldstar_name)
                column_count += 1
                worksheet.write(row_count, column_count, inventory.commodity)
                column_count += 1
                worksheet.write(row_count, column_count, str('{0:,.0f}'.format(inventory.total_received_quantity)),format_for_numeric_without_bold)
                column_count += 1
                worksheet.write(row_count, column_count, str('{0:,.2f}'.format(inventory.temp_received_weight) + ' oz'),
                                format_for_numeric_without_bold)
                column_count += 1
                is_data_exists = True
                row_count += 1
                column_count = 0
        else:
            worksheet.write(row_count, column_count, 'N/A')
            column_count += 1
            worksheet.write(row_count, column_count, 'N/A')
            column_count += 1
            worksheet.write(row_count, column_count, str('{0:,.0f}'.format(0)),
                            format_for_numeric_without_bold)
            column_count += 1
            worksheet.write(row_count, column_count, str('{0:,.2f}'.format(0) + ' oz'),
                            format_for_numeric_without_bold)
            column_count += 1
            is_data_exists = True
            row_count += 1
        self.add_total_table(row_count, worksheet, bold, format_for_numeric_bold, format_for_numeric_without_bold)

        return is_data_exists

    @api.one
    def add_total_table(self, row_count, worksheet, bold, format_for_numeric_bold, format_for_numeric_without_bold):

        row_number = row_count + 3
        column_count = 4
        worksheet.write(row_number, column_count, '')
        row_number += 1
        worksheet.write(row_number, column_count, 'Gold')
        row_number += 1
        worksheet.write(row_number, column_count, 'Silver')
        row_number += 1
        worksheet.write(row_number, column_count, 'Platinum')
        row_number += 1
        worksheet.write(row_number, column_count, 'Palladium')
        row_number += 1
        worksheet.write(row_number, column_count, 'Grand Total', bold)
        row_number = row_count + 3
        column_count += 1

        worksheet.write(row_number, column_count, 'Total Units', bold)
        row_number += 1
        worksheet.write(row_number, column_count, str('{0:,.0f}'.format(self.customers.total_gold)),
                        format_for_numeric_without_bold)
        row_number += 1
        worksheet.write(row_number, column_count, str('{0:,.0f}'.format(self.customers.total_silver)),
                        format_for_numeric_without_bold)
        row_number += 1
        worksheet.write(row_number, column_count, str('{0:,.0f}'.format(self.customers.total_platinum)),
                        format_for_numeric_without_bold)
        row_number += 1
        worksheet.write(row_number, column_count, str('{0:,.0f}'.format(self.customers.total_palladium)),
                        format_for_numeric_without_bold)
        row_number += 1
        worksheet.write(row_number, column_count, str('{0:,.0f}'.format(self.customers.total)), format_for_numeric_bold)
        row_number = row_count + 3
        column_count += 1

        worksheet.write(row_number, column_count, 'Total Weight', bold)
        row_number += 1
        worksheet.write(row_number, column_count, str('{0:,.2f}'.format(self.customers.c_gold_weight) + ' oz'),
                        format_for_numeric_without_bold)
        row_number += 1
        worksheet.write(row_number, column_count, str('{0:,.2f}'.format(self.customers.c_silver_weight) + ' oz'),
                        format_for_numeric_without_bold)
        row_number += 1
        worksheet.write(row_number, column_count, str('{0:,.2f}'.format(self.customers.c_platinum_weight) + ' oz'),
                        format_for_numeric_without_bold)
        row_number += 1
        worksheet.write(row_number, column_count, str('{0:,.2f}'.format(self.customers.c_palladium_weight) + ' oz'),
                        format_for_numeric_without_bold)
        row_number += 1
        worksheet.write(row_number, column_count, str('{0:,.2f}'.format(self.customers.c_total_weight) + ' oz'),
                        format_for_numeric_bold)
        row_number = row_count + 3
        column_count += 1

        worksheet.write(row_number, column_count, 'Total Value', bold)
        row_number += 1
        worksheet.write(row_number, column_count, '$ ' + str('{0:,.2f}'.format(self.customers.c_total_gold_value)),
                        format_for_numeric_without_bold)
        row_number += 1
        worksheet.write(row_number, column_count, '$ ' + str('{0:,.2f}'.format(self.customers.c_total_silver_value)),
                        format_for_numeric_without_bold)
        row_number += 1
        worksheet.write(row_number, column_count, '$ ' + str('{0:,.2f}'.format(self.customers.c_total_platinum_value)),
                        format_for_numeric_without_bold)
        row_number += 1
        worksheet.write(row_number, column_count, '$ ' + str('{0:,.2f}'.format(self.customers.c_total_palladium_value)),
                        format_for_numeric_without_bold)
        row_number += 1
        worksheet.write(row_number, column_count, '$ ' + str('{0:,.2f}'.format(self.customers.c_total_value)),
                        format_for_numeric_bold)

    @api.model
    def default_get(self, fields):
        res = super(CustodianReports, self).default_get(fields)
        if self.env.user.custodian_id:
            res['custodian_id'] = self.env.user.custodian_id.id
            # res['customers'] = self._context['active_id']
        return res


    name = fields.Char()
    report_types = fields.Selection(selection=[
        ('current_inventory_excel', 'Current Inventory (Excel Format)'),
        ('customer_metal_activity_excel', 'Customer Metal Activity (Excel Format)'),
        ('current_inventory_pdf', 'Current Inventory'),
        ('customer_metal_activity_pdf', 'Customer Metal Activity'),
        ('custodian_inventory_by_customer', 'Custodian Inventory By Customer (Full)'),
        ('custodian_inventory_by_customer_segregated', 'Custodian Inventory By Customer (Segregated)'),
        ('custodian_inventory_by_customer_commingled', 'Custodian Inventory By Customer (Commingled)'),
    ], required=True)

    customers = fields.Many2one('amgl.customer', string='Customers')
    show_download_report_button = fields.Boolean(default=False)
    show_customers = fields.Boolean(default=False)
    custodian_id = fields.Many2one('amgl.custodian', string="Custodian", required=True)