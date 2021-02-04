# -*- coding: utf-8 -*-

import base64
import datetime
import inflect
import xlsxwriter
from dateutil import parser
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class DepositEmailWizard(models.TransientModel):
    _name = 'amgl.deposit.email.wizard'

    def add_report_to_attachment(self, report_result, report_name):
        attachment = self.env['ir.attachment'].create({'name': report_name,
                                                       'datas': base64.b64encode(report_result),
                                                       'datas_fname': report_name,
                                                       'res_model': 'res.users',
                                                       'res_id': 1, })
        return attachment.id

    def send_deposit_batch_email(self):
        order_line = self.env['amgl.order_line'].search([('id', '=', self._context['active_id'])])
        order_lines = self.env['amgl.order_line'].search(
            [('is_master_records', '=', False), ('batch_number', '=', order_line.batch_number)])
        batch_number = ''
        if self.existing_deposit_batch and not self.existing_batch_number:
            raise ValidationError("Existing batch number must be selected in order to merge.")
        if self.existing_batch_number:
            temp_batch_number = self.existing_batch_number.split(' ', 1)[0]
            batch_number = temp_batch_number[1:]
            self.validate_batch_merger(order_lines, batch_number)

        customer = order_line.customer_id
        text = self.build_template_using_data(customer, order_line)
        template = self.env.ref('amgl.deposit_batch_email_template', raise_if_not_found=True)
        data_object = {
            'ids': order_lines.ids,
            'model': 'amgl.order_line',
            'form': order_lines.ids
        }
        if self.existing_batch_number:
            self.merge_batches(order_lines, batch_number)
        attachment_file_name = order_line.batch_number + ' Deposit for #' + str(
            customer.account_number if 'Gold' not in customer.custodian_id.name else customer.gst_account_number)
        excel_attachment_id = self.create_excel_file(attachment_file_name, order_lines)
        report_result = self.env['report'].get_pdf(order_lines.ids, 'amgl.customer_orderlines_batch_report',
                                                   data=data_object)
        attachment_id = self.add_report_to_attachment(report_result, attachment_file_name + '.pdf')
        email_subject = 'Deposit Confirmation ' + order_line.batch_number
        additional_email_subject_info = self.get_additional_email_subject_info()
        if additional_email_subject_info:
            email_subject = additional_email_subject_info + email_subject

        email_cc = self.env['ir.config_parameter'].get_param('email.cc')

        emails = self.get_email_for_deposit_bacth_email(customer.custodian_id.name)

        mail_id = template.with_context(email_body=text,
                                        email_subject=email_subject,
                                        email_cc=email_cc,
                                        email_to=emails
                                        ).send_mail(
            1, force_send=False, raise_exception=True,
            email_values={'attachment_ids': [attachment_id, excel_attachment_id]}
        )

        order_lines = self.env['amgl.order_line'].search([('batch_number', '=', order_line.batch_number)])
        for item in order_lines:
            item.write({
                'batch_email_sent': True
            })
        if self.deposit_fees > 0.0:
            self.env['amgl.fees'].create({
                'inbound_fees': self.deposit_fees,
                'customer_id': customer.id,
                'order_line_id': order_line.id
            })

        base_url = self.env['ir.config_parameter'].get_param('amgl.live.url')
        return {
            'type': 'ir.actions.act_url',
            'url': str(base_url) + '/amgl/static/html/deposit_email_sent.html',
            'target': 'self'
        }

    def get_email_for_deposit_bacth_email(self, cust_name):
        email_groups = self.env['amgl.email.group'].search([])
        emails = ''
        for item in email_groups:
            if cust_name in item.name:  # send emails to custodian group
                emails += ',' + item.emails
            if 'Headquarter' in item.name:  # send emails to Headquarter group
                emails += ',' + item.emails

        emails = emails.lstrip(",")
        emails = emails.rstrip(",")
        return emails

    def get_additional_email_subject_info(self):
        base_url = self.env['ir.config_parameter'].get_param('amgl.live.url')
        subject = ''
        if 'irastorage' not in base_url:
            if 'localhost' in base_url:
                subject = '(Test: Localhost) '
            elif 'odev' in base_url:
                subject = '(Test: Odev) '
        return subject

    def create_excel_file(self, attachment_file_name, orderlines):
        bold, file_name, workbook, worksheet = self.configure_workbook(attachment_file_name)
        DepositEmailWizard.add_headers(bold, worksheet, workbook)
        row_count = 2
        attachment_id = 0
        total_cells_format = workbook.add_format({'bold': True})
        total_cells_format.set_border(1)
        is_data_exists = self.add_rows_in_worksheet(row_count, worksheet, workbook, bold, orderlines)
        workbook.close()
        if is_data_exists:
            attachment = self.add_file_in_attachment(file_name)
            attachment_id = attachment.id
        return attachment_id

    def configure_workbook(self, attachment_file_name):
        file_name = "/excel/" + attachment_file_name + '.xlsx'
        workbook = xlsxwriter.Workbook(file_name)
        worksheet = workbook.add_worksheet('Customer Deposit Details')
        bold = workbook.add_format({'bold': True})
        return bold, file_name, workbook, worksheet

    @staticmethod
    def add_headers(bold, worksheet, workbook):
        row_count = 0
        column_count = 0
        worksheet.write(row_count, column_count, 'First Name', bold)
        worksheet.write(row_count, column_count + 1, 'Last Name', bold)
        worksheet.write(row_count, column_count + 2, 'Account Number', bold)
        worksheet.write(row_count, column_count + 3, 'Account Type', bold)
        worksheet.write(row_count, column_count + 4, 'Batch Number', bold)
        worksheet.write(row_count, column_count + 5, 'Custodian', bold)
        worksheet.write(row_count, column_count + 6, 'Product', bold)
        worksheet.write(row_count, column_count + 7, 'Commodity', bold)
        worksheet.write(row_count, column_count + 8, 'Quantity', bold)
        worksheet.write(row_count, column_count + 9, 'Total Weight', bold)
        worksheet.write(row_count, column_count + 10, 'Date', bold)

    def add_rows_in_worksheet(self, row_count, worksheet, workbook, bold, orderlines):
        is_data_exists = False
        format_for_numeric_bold = workbook.add_format({'bold': True, 'align': 'right', })
        format_for_numeric_without_bold = workbook.add_format({'align': 'right'})
        row_count = 1
        column_count = 0
        if orderlines:
            for item in orderlines:
                worksheet.write(row_count, column_count, item.customer_id.first_name)
                column_count += 1
                worksheet.write(row_count, column_count, item.customer_id.last_name)
                column_count += 1
                worksheet.write(row_count, column_count,
                                item.customer_id.account_number if 'Gold' not in item.customer_id.custodian_id.name else item.customer_id.gst_account_number)
                column_count += 1
                worksheet.write(row_count, column_count, item.customer_id.account_type)
                column_count += 1
                worksheet.write(row_count, column_count, item.batch_number)
                column_count += 1
                worksheet.write(row_count, column_count, item.customer_id.custodian_id.name)
                column_count += 1
                worksheet.write(row_count, column_count, item.products.goldstar_name)
                column_count += 1
                worksheet.write(row_count, column_count, item.commodity)
                column_count += 1
                worksheet.write(row_count, column_count, int(item.total_received_quantity),
                                format_for_numeric_without_bold)
                column_count += 1
                worksheet.write(row_count, column_count, str('{0:,.2f}'.format(item.temp_received_weight) + ' oz'),
                                format_for_numeric_without_bold)
                column_count += 1
                worksheet.write(row_count, column_count,
                                str(datetime.datetime.strptime(item.date_received, '%Y-%m-%d').strftime("%m/%d/%Y")),
                                format_for_numeric_without_bold)
                column_count += 1
                is_data_exists = True
                row_count += 1
                column_count = 0
        else:
            worksheet.write(row_count, column_count, orderlines[0].customer_id.first_name)
            column_count += 1
            worksheet.write(row_count, column_count, orderlines[0].customer_id.last_name)
            column_count += 1
            worksheet.write(row_count, column_count,
                            orderlines[0].customer_id.account_number if 'Gold' not in orderlines[
                                0].customer_id.custodian_id.name else orderlines[0].customer_id.gst_account_number)
            column_count += 1
            worksheet.write(row_count, column_count, orderlines[0].customer_id.account_type)
            column_count += 1
            worksheet.write(row_count, column_count, 'N/A')
            column_count += 1
            worksheet.write(row_count, column_count, 'N/A')
            column_count += 1
            worksheet.write(row_count, column_count, 'N/A')
            column_count += 1
            worksheet.write(row_count, column_count, 'N/A')
            column_count += 1
            worksheet.write(row_count, column_count, str('{0:,.2f}'.format(0)),
                            format_for_numeric_without_bold)
            column_count += 1
            worksheet.write(row_count, column_count, str('{0:,.2f}'.format(0) + ' oz'),
                            format_for_numeric_without_bold)
            column_count += 1
            worksheet.write(row_count, column_count, 'N/A',
                            format_for_numeric_without_bold)
            column_count += 1
            is_data_exists = True
            row_count += 1

        return is_data_exists

    def add_file_in_attachment(self, file_name):
        byte_data = 0
        with open(file_name, "rb") as xlfile:
            byte_data = xlfile.read()
        attachment = self.env['ir.attachment'].create({'name': file_name.replace('/excel/', ''),
                                                       'datas': base64.b64encode(byte_data),
                                                       'datas_fname': file_name.replace('/excel/', ''),
                                                       'res_model': 'res.users',
                                                       'res_id': 1, })
        return attachment

    def build_template_using_data(self, customer, order_line):
        formatted_date = str(datetime.datetime.strptime(order_line.date_received, '%Y-%m-%d').strftime("%m/%d/%Y"))
        text = self.email_body.encode('ascii', 'ignore')
        text = text.replace('[Custodian]', customer.custodian_id.name)
        text = text.replace('[deposit_date]', formatted_date)
        text = text.replace('[account_name]', customer.full_name)
        if 'Gold' in customer.custodian_id.name:
            text = text.replace('[account_number]', customer.gst_account_number)
        else:
            text = text.replace('[account_number]', customer.account_number)
        text = text.replace('[batch_number]', order_line.batch_number)
        return text

    def validate_batch_merger(self, order_lines, batch_number):
        existing_batch_order_lines = self.env['amgl.order_line'].search([('is_master_records', '=', False),
                                                                         ('batch_number', '=', batch_number)],
                                                                        order='batch_number desc')
        list_existing_batch_products = []
        list_current_batch_products = []
        for existing_batch_order in existing_batch_order_lines:
            list_existing_batch_products.append(existing_batch_order.products.goldstar_name)
        for current_batch_order in order_lines:
            list_current_batch_products.append(current_batch_order.products.goldstar_name)
        result = all(elem in list_existing_batch_products for elem in list_current_batch_products)
        if not result:
            raise ValidationError('Batch cannot be merged as both batch contain different products!')

    def merge_batches(self, order_lines, batch_number):
        for item in order_lines:
            # Updating merged product
            note = 'Batch merged with #' + batch_number
            self.env.cr.execute("""
                                    Update amgl_order_line set merged_notes = %s
                                    WHERE id = %s""",
                                [note, item.id])

    @api.onchange('existing_deposit_batch')
    def onchange_existing_deposit_batch_check(self):
        if self.existing_deposit_batch:
            self.deposit_fees = 0.00
            return {'existing_batch_number': [self.get_existing_batch_number()]}
        elif self.existing_batch_number:
            self.existing_batch_number = []

    @api.model
    def default_get(self, fields):
        res = super(DepositEmailWizard, self).default_get(fields)
        res['first_deposit_date'] = self.get_first_deposit_date()
        res['customer_grace_period'] = self.get_customer_grace_period()
        res['deposit_bonus_days_remaining'] = self.get_deposit_bonus_days_remaining()
        res['completed_deposits_before'] = self.get_completed_deposits_till_now()
        return res

    def get_first_deposit_date(self):
        order_line = self.env['amgl.order_line'].search([('id', '=', self._context['active_id'])])
        customer_id = order_line.customer_id.id
        customer_order_lines = self.env['amgl.order_line'].search(
            ['&', ('customer_id', '=', customer_id), ('is_master_records', '=', False)], order='date_received asc')
        return customer_order_lines[0].date_received

    def get_customer_grace_period(self):
        order_line = self.env['amgl.order_line'].search([('id', '=', self._context['active_id'])])
        grace_period = order_line.customer_id.grace_period if order_line.customer_id.grace_period else 'None'
        if grace_period:
            grace_period = str(inflect.engine().number_to_words(grace_period).capitalize())

        return grace_period

    def get_completed_deposits_till_now(self):
        order_id = self._context['active_id']
        current_order_line = self.env['amgl.order_line'].search([('id', '=', order_id)])
        customer_order_lines = self.env['amgl.order_line'].search(
            [('customer_id', '=', current_order_line.customer_id.id), ('id', '!=', order_id),
             ('is_master_records', '=', False), ('batch_email_sent', '=', True)])
        if customer_order_lines:
            return str(len(customer_order_lines))
        else:
            return '0'

    def get_deposit_bonus_days_remaining(self):
        order_line = self.env['amgl.order_line'].search([('id', '=', self._context['active_id'])])
        customer_id = order_line.customer_id.id
        customer_order_lines = self.env['amgl.order_line'].search(
            ['&', ('customer_id', '=', customer_id), ('is_master_records', '=', False)], order='date_received asc')
        first_deposit_date = customer_order_lines[0].date_received
        if order_line.customer_id.grace_period:
            temp_end_of_period = parser.parse(first_deposit_date) + relativedelta(
                months=order_line.customer_id.grace_period)
            end_of_period = parser.parse(str(temp_end_of_period)).date()
            today_date = datetime.datetime.now().date()
            if today_date > end_of_period:
                return 'Bonus Time Passed !'
            if today_date < end_of_period:
                return str(end_of_period - today_date).split(',')[0] + ' remaining !'
            if today_date == end_of_period:
                return 'Last Day of bonus period !'
        else:
            return 'No bonus period allotted !'

    def get_existing_batch_number(self):
        batch_numbers = []
        if self._context.get('active_id'):
            order_line = self.env['amgl.order_line'].search([('id', '=', self._context['active_id'])])
            self.env.cr.execute("select distinct batch_number from amgl_order_line where merged_notes Is Null and  "
                                "batch_number not like '%W%' and products =" + str(
                order_line.products.id) + " and batch_email_sent = True and "
                                          "customer_id = " + str(
                order_line.customer_id.id) + " order by batch_number asc")
            temp_batch_numbers = self.env.cr.fetchall()
            if temp_batch_numbers:
                customer_name = order_line.customer_id.full_name
                custodian_name = str(order_line.customer_id.custodian_id.name)
                customer_account_number = order_line.customer_id.account_number
                if 'Gold' in custodian_name:
                    customer_account_number = order_line.customer_id.gst_account_number
                for item in temp_batch_numbers:
                    encoded_batch_number = item[0].encode('ascii', 'ignore')
                    detailed_batch_info = '#' + encoded_batch_number + ' ' + customer_name + ' (#' + customer_account_number + ')'
                    batch_numbers.append((detailed_batch_info, detailed_batch_info))
        return batch_numbers

    name = fields.Html(string="Email Body")
    email_body = fields.Html(string="Email Body",
                             default="Dear [Custodian], <br /><br /> Metal was recently deposited into account #[account_number], [account_name]."
                                     " Please see attachment for full deposit details. "
                                     "<br /><p></p><br /><table> "
                                     "<tr> <td><b>Deposit Ref.:</b></td>  <td style='padding:left:30px;'>[batch_number]</td> </tr>"
                                     "<tr> <td><b>Deposit Date:</b></td>  <td style='padding:left:30px;'>[deposit_date]</td> </tr>"
                                     "<tr> <td><b>Deposit Location:</b></td>  <td style='padding:left:30px;'>AMGL Las Vegas</td> </tr>"
                                     "<tr> <td><b>Account Name:</b></td>  <td style='padding:left:30px;'>[account_name]</td> </tr>"
                                     "<tr> <td><b>Account Number:</b></td>  <td style='padding:left:30px;'>[account_number]</td> </tr>"
                                     " </table><br /><br /><p></p><br />"
                                     "If you have any questions, please contact irastorage@amark.com"
                                     "<br /><p></p><br />"
                                     "Thank you,<br /><p></p><br />"
                                     "AMGL IRA Storage Team"
                             )
    mmr_id = fields.Many2one('amgl.metal_movement', string='MMR Id')
    Preview_batch_details = fields.Char(string='Preview Batch Details: ')
    order_line_id = fields.Many2one('amgl.order_line', string='OrderLine Id')
    first_deposit_date = fields.Date(string='First Deposit Date')
    deposit_bonus_days_remaining = fields.Char(string='Bonus Days Remainng')
    deposit_fees = fields.Float(string='Deposit Fees')
    existing_deposit_batch = fields.Boolean('Existing Deposit Batch?')
    existing_batch_number = fields.Selection(selection='get_existing_batch_number', string='Batch Number')
    completed_deposits_before = fields.Char(string='Completed Deposits Till Now')
    customer_grace_period = fields.Char(string='No Fee Duration',)
