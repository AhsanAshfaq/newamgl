# -*- coding: utf-8 -*-
import base64
import logging
import xlsxwriter
from datetime import datetime, timedelta

import dateutil.relativedelta

from odoo import models, fields

_logger = logging.getLogger(__name__)


class EmailScheduler(models.Model):
    _name = 'amgl.email.scheduler'

    def send_mmr_reminder_email(self):
        mmr_list = self.env['amgl.metal_movement'].search([('state', '!=', 'completed')])
        for mmr in mmr_list:
            number_of_packages = int(mmr.number_of_packages)
            for item in range(number_of_packages):
                if not mmr['package' + str(item + 1)] or (not mmr['vault_review']) or (not mmr['vault_complete']):
                    first_execution_date = datetime.strptime(str(mmr.create_date), '%Y-%m-%d %H:%M:%S') + timedelta(
                        hours=24)
                    if mmr.reminder_sent_date:
                        last_sent_date = datetime.strptime(str(mmr.reminder_sent_date), '%Y-%m-%d %H:%M:%S')
                        next_execution_date = datetime.strptime(str(last_sent_date), '%Y-%m-%d %H:%M:%S') + timedelta(
                            hours=24)
                    else:
                        next_execution_date = datetime.strptime(str(mmr.create_date), '%Y-%m-%d %H:%M:%S') + timedelta(
                            hours=24)
                    current_date = datetime.strptime(str(datetime.now()), '%Y-%m-%d %H:%M:%S.%f')

                    if mmr.is_reminder_sent:
                        if current_date == next_execution_date or current_date > next_execution_date :
                            self.send_reminder_email(mmr)
                    else:
                        if (current_date == first_execution_date or
                                current_date > first_execution_date):
                            self.send_reminder_email(mmr)

    def send_reminder_email(self, mmr):
        package_template = self.construct_packages_template(mmr)
        template = self.env.ref('amgl.mmr_package_number_reminder', raise_if_not_found=True)
        base_url = self.env['ir.config_parameter'].get_param('amgl.live.url')
        creator_of_mmr = self.env['res.users'].search([('id', '=', mmr.create_uid.id)])
        mmr_menu = self.env['ir.ui.menu'].search([('name', '=', 'Withdrawal')])
        mmr_windows_action = self.env['ir.actions.act_window'].search([('res_model', '=', 'amgl.metal_movement')],limit=1)
        temp_mmr_link = base_url + "/web#id=" + str(
            mmr.id) + "&view_type=form&model=amgl.metal_movement&action=" + str(mmr_windows_action.id) +"&menu_id=" + str(mmr_menu.id)
        formated_mmr_date = str(datetime.strptime(mmr.date_create, '%Y-%m-%d').strftime("%m/%d/%Y"))
        email_subject = "Metal Move Request Data Missing"
        additional_email_subject_info = self.get_additional_email_subject_info()
        if additional_email_subject_info:
            email_subject = additional_email_subject_info + email_subject
        user_groups = ['Administrator', 'Sub-Admins']
        user_for_email = self.get_users_for_email(user_groups)
        email_cc = self.env['ir.config_parameter'].get_param('email.cc')
        for user_email in user_for_email:
            template.with_context(mmr_link=temp_mmr_link,
                                  creator_of_mmr_name = creator_of_mmr.name,
                                  date=formated_mmr_date,
                                  ref=str(mmr.reference),
                                  fapprove=str(mmr.first_approve.name),
                                  sapprove=str(mmr.second_approve.name),
                                  customer=str(mmr.customer.full_name),
                                  custodian=str(mmr.custodian.name),
                                  mmt=str(mmr.metal_movement_type),
                                  name=str(mmr.name),
                                  mmf_accountnumber=str(mmr.mmf_account_number),
                                  mmf_accounttype=str(mmr.mmf_account_type),
                                  mmt_name=str(mmr.mmt_name if mmr.mmt_name is not False else ''),
                                  mmt_address=str(mmr.mmt_address if mmr.mmt_address is not False else ''),
                                  mmt_account=str(mmr.mmt_account_number if mmr.mmt_account_number is not False else ''),
                                  mmr_number=mmr.mmr_number,
                                  package_template=package_template,
                                  email_cc = email_cc,
                                  email_subject=email_subject).send_mail(
                user_email[0], force_send=False, raise_exception=True
            )
        self.env.cr.execute(
            'UPDATE amgl_metal_movement set is_reminder_sent=True,reminder_sent_date=%s where id = %s',
            (datetime.now(), mmr.id))

    def get_additional_email_subject_info(self):
        base_url = self.env['ir.config_parameter'].get_param('amgl.live.url')
        subject = ''
        if 'irastorage' not in base_url:
            if 'localhost' in base_url:
                subject = '(Test: Localhost) '
            elif 'odev' in base_url:
                subject = '(Test: Odev) '
        return subject

    def get_users_for_email(self,user_groups):
        users_for_email = []
        for group in user_groups:
            self.env.cr.execute(
                "select * from res_users where id in (select uid from res_groups_users_rel where gid in (select id from res_groups where name = '" + str(group) + "' ))")
            users = self.env.cr.fetchall()
            if users:
                for user in users:
                    users_for_email.append(user)
        return users_for_email

    @staticmethod
    def construct_packages_template(mmr):
        package_template = """<strong style="color:black;">PACKAGE TRACKING</strong><table> """
        if mmr.p1_boolean:
            package_template += '''
                                <tr>
                                    <td>
                                        Package1:
                                    </td>
                                    <td style="padding-left:120px;">'''
            if mmr.package1:
               package_template += mmr.package1 + '</td></tr>'
            else:
                package_template += '</td></tr>'
        if mmr.p2_boolean:
            package_template += '''
                                            <tr>
                                                <td>
                                                    Package2:
                                                </td>
                                                <td style="padding-left:120px;">'''
            if mmr.package2:
                package_template += mmr.package2 + '</td></tr>'
            else:
                package_template += '</td></tr>'
        if mmr.p3_boolean:
            package_template += '''
                                            <tr>
                                                <td>
                                                    Package3:
                                                </td>
                                                <td style="padding-left:120px;">'''
            if mmr.package3:
                package_template += mmr.package3 + '</td></tr>'
            else:
                package_template += '</td></tr>'
        if mmr.p4_boolean:
            package_template += '''
                                            <tr>
                                                <td>
                                                    Package4:
                                                </td>
                                                <td style="padding-left:120px;">'''
            if mmr.package4:
                package_template += mmr.package4 + '</td></tr>'
            else:
                package_template += '</td></tr>'
        if mmr.p5_boolean:
            package_template += '''
                                                        <tr>
                                                            <td>
                                                                Package5:
                                                            </td>
                                                            <td style="padding-left:120px;">'''
            if mmr.package5:
                package_template += mmr.package5 + '</td></tr>'
            else:
                package_template += '</td></tr>'
        if mmr.p6_boolean:
            package_template += '''
                                                        <tr>
                                                            <td>
                                                                Package6:
                                                            </td>
                                                            <td style="padding-left:120px;">'''
            if mmr.package6:
                package_template += mmr.package6 + '</td></tr>'
            else:
                package_template += '</td></tr>'
        if mmr.p7_boolean:
            package_template += '''
                                            <tr>
                                                <td>
                                                    Package7:
                                                </td>
                                                <td style="padding-left:120px;">'''
            if mmr.package7:
                package_template += mmr.package7 + '</td></tr>'
            else:
                package_template += '</td></tr>'
        if mmr.p8_boolean:
            package_template += '''
                                            <tr>
                                                <td>
                                                    Package8:
                                                </td>
                                                <td style="padding-left:120px;">'''
            if mmr.package8:
                package_template += mmr.package8 + '</td></tr>'
            else:
                package_template += '</td></tr>'
        if mmr.p9_boolean:
            package_template += '''
                                            <tr>
                                                <td>
                                                    Package9:
                                                </td>
                                                <td style="padding-left:120px;">'''
            if mmr.package9:
                package_template += mmr.package9 + '</td></tr>'
            else:
                package_template += '</td></tr>'
        if mmr.p10_boolean:
            package_template += '''
                                            <tr>
                                                <td>
                                                    Package10:
                                                </td>
                                                <td style="padding-left:120px;">'''
            if mmr.package10:
                package_template += mmr.package10 + '</td></tr>'
            else:
                package_template += '</td></tr>'
        if mmr.p11_boolean:
            package_template += '''
                                            <tr>
                                                <td>
                                                    Package11:
                                                </td>
                                                <td style="padding-left:120px;">'''
            if mmr.package11:
                package_template += mmr.package11 + '</td></tr>'
            else:
                package_template += '</td></tr>'
        if mmr.p12_boolean:
            package_template += '''
                                            <tr>
                                                <td>
                                                    Package12:
                                                </td>
                                                <td style="padding-left:120px;">'''
            if mmr.package12:
                package_template += mmr.package12 + '</td></tr>'
            else:
                package_template += '</td></tr>'
        if mmr.p13_boolean:
            package_template += '''
                                            <tr>
                                                <td>
                                                    Package13:
                                                </td>
                                                <td style="padding-left:120px;">'''
            if mmr.package13:
                package_template += mmr.package13 + '</td></tr>'
            else:
                package_template += '</td></tr>'
        if mmr.p14_boolean:
            package_template += '''
                                            <tr>
                                                <td>
                                                    Package14:
                                                </td>
                                                <td style="padding-left:120px;">'''
            if mmr.package14:
                package_template += mmr.package14 + '</td></tr>'
            else:
                package_template += '</td></tr>'
        if mmr.p15_boolean:
            package_template += '''
                                            <tr>
                                                <td>
                                                    Package15:
                                                </td>
                                                <td style="padding-left:120px;">'''
            if mmr.package15:
                package_template += mmr.package15 + '</td></tr>'
            else:
                package_template += '</td></tr>'
        if mmr.p16_boolean:
            package_template += '''
                                            <tr>
                                                <td>
                                                    Package16:
                                                </td>
                                                <td style="padding-left:120px;">'''
            if mmr.package16:
                package_template += mmr.package16 + '</td></tr>'
            else:
                package_template += '</td></tr>'
        if mmr.p17_boolean:
            package_template += '''
                                            <tr>
                                                <td>
                                                   Package17:
                                                </td>
                                                <td style="padding-left:120px;">'''
            if mmr.package17:
                package_template += mmr.package17 + '</td></tr>'
            else:
                package_template += '</td></tr>'
        if mmr.p18_boolean:
            package_template += '''
                                            <tr>
                                                <td>
                                                    Package18:
                                                </td>
                                                <td style="padding-left:120px;">'''
            if mmr.package18:
                package_template += mmr.package18 + '</td></tr>'
            else:
                package_template += '</td></tr>'
        if mmr.p19_boolean:
            package_template += '''
                                            <tr>
                                                <td>
                                                    Package19:
                                                </td>
                                                <td style="padding-left:120px;">'''
            if mmr.package19:
                package_template += mmr.package19 + '</td></tr>'
            else:
                package_template += '</td></tr>'
        if mmr.p20_boolean:
            package_template += '''
                                <tr>
                                    <td>
                                        Package20:
                                    </td>
                                    <td style="padding-left:120px;">'''
            if mmr.package20:
                package_template += mmr.package20 + '</td></tr>'
            else:
                package_template += '</td></tr>'
        return package_template + '</table>'

    def process_email_scheduler_queue(self):

        custodian = self.env['amgl.custodian'].search([('name', 'ilike', 'Gold')], limit=1)
        customers = self.env['amgl.customer'].search([('custodian_id', '=', custodian.id)])
        EmailScheduler.create_csv_files(self, customers)

    @staticmethod
    def create_csv_files(self, customers):
        EmailScheduler.generate_full_transaction_csv(customers, self)
        EmailScheduler.generate_daily_transaction_csv(customers, self)
        EmailScheduler.generate_new_accounts_csv(customers)

    @staticmethod
    def generate_new_accounts_csv(customers):
        new_accounts_csv_dir = '/home/ahsan/AMARK/ExportFiles/' + datetime.now().strftime(
            "%B %Y") + ' NEW ACCOUNTS BILLING.csv'
        with open(new_accounts_csv_dir, 'wb') as f:
            for customer in customers:
                init_date = datetime.strptime(customer.date_opened, '%Y-%m-%d').strftime('%m/%d/%y')
                row = customer.account_number + ','
                row += customer.gst_account_number + ',' if customer.gst_account_number else '' + ','
                row += 'IRA-NS ,' if customer.account_type == 'Commingled' else 'IRA-S ,'
                row += init_date + ','
                row += customer.full_name.replace(',', '') + ','
                row += str(int(customer.total_account_value)) + ','
                row += '$' + str(round(customer.total_fees, 2))
                f.write(row)
                f.write('\n')

    @staticmethod
    def generate_full_transaction_csv(customers, self):
        daily_transaction_csv_dir = '/home/ahsan/AMARK/ExportFiles/Goldstar - Tranfile All ' + datetime.now().strftime(
            "%d-%B-%Y") + '.csv'
        with open(daily_transaction_csv_dir, 'wb') as f:
            for customer in customers:
                customer_orders = self.env['amgl.order_line']. \
                    search(['&', ('customer_id', '=', customer.id), ('state', '=', 'completed')])
                for customer_order in customer_orders:
                    init_date = datetime.strptime(customer.create_date, '%Y-%m-%d %H:%M:%S').strftime('%m/%d/%y')
                    row = customer.gst_account_number + ',' if customer.gst_account_number else '' + ','
                    row += customer.full_name + ','
                    row += customer.account_number + ','
                    row += str(init_date) + ','
                    row += str(customer_order.transaction_number) + ','
                    row += ' PS ,' if customer_order.metal_movement_id else 'PR ,'
                    row += customer_order.products.gs_product_code + ',' if customer_order.products.gs_product_code is not False else '' + ','
                    row += str(customer_order.total_received_quantity) + ',AMGL,'
                    row += customer.amark_customer_code + ', ' if customer.amark_customer_code is not False else ', '
                    f.write(row)
                    f.write('\n')

    @staticmethod
    def generate_daily_transaction_csv(customers, self):
        daily_transaction_csv_dir = '/home/ahsan/AMARK/ExportFiles/Goldstar - Tranfile Current Day ' + datetime.now().strftime(
            "%d-%B-%Y") + '.csv'
        with open(daily_transaction_csv_dir, 'wb') as f:
            for customer in customers:
                customer_orders = self.env['amgl.order_line']. \
                    search(['&', ('customer_id', '=', customer.id), ('state', '=', 'completed')])
                for customer_order in customer_orders:
                    if customer_order.date_created == str(datetime.now().date()) and customer_order.is_master_records == False:
                        init_date = datetime.strptime(customer.create_date, '%Y-%m-%d %H:%M:%S').strftime(
                            '%m/%d/%y')
                        row = customer.gst_account_number + ',' if customer.gst_account_number else '' + ','
                        row += customer.full_name + ','
                        row += customer.account_number + ','
                        row += str(init_date) + ','
                        row += str(customer_order.transaction_number) + ','
                        row += ' PS ,' if customer_order.metal_movement_id else 'PR ,'
                        row += customer_order.products.gs_product_code + ',' if customer_order.products.gs_product_code is not False else '' + ','
                        row += str(customer_order.total_received_quantity) + ',AMGL,'
                        row += customer.amark_customer_code + ', ' if customer.amark_customer_code is not False else ', '
                        f.write(row)
                        f.write('\n')

    # <editor-fold desc="Static Methods">

    @staticmethod
    def go_month_back(date_time):
        str_date = date_time
        d = datetime.datetime.strptime("2013-03-28", "%Y-%m-%d")
        d2 = d - dateutil.relativedelta.relativedelta(months=1)
        return d2;

    @staticmethod
    def get_last_day(date_time):
        next_month = date_time.replace(day=28) + datetime.timedelta(days=4)  # this will never fail
        return next_month - datetime.timedelta(days=next_month.day)

    @staticmethod
    def get_first_day(date_time):
        today_date = date_time
        if today_date.day > 25:
            today_date += datetime.timedelta(7)
        return today_date.replace(day=1)

    # </editor-fold>

    # <editor-fold desc="Create Excel File -- For later use">

    @staticmethod
    def create_excel_file(self, customers):
        bold, file_name, workbook, worksheet = EmailScheduler.configure_workbook()
        EmailScheduler.add_headers(bold, worksheet)
        row_count = 2
        is_data_exists = EmailScheduler.add_rows_in_worksheet(customers, row_count, self, worksheet)
        workbook.close()
        if is_data_exists:
            attachment = EmailScheduler.add_file_in_attachment(file_name, self)
            email_id = EmailScheduler.send_email_with_attachment(attachment, self)
            all_scheduler_items = self.env['amgl.email.scheduler'].search([])
            self.env['amgl.email.scheduler'].create({
                'name': 'Gold Star Export Email',
                'numberOfUpdates': len(all_scheduler_items) + 1,
                'lastModified': datetime.now(),
                'mail_id': email_id,
                'attachment_id': attachment.id
            })

    @staticmethod
    def configure_workbook():
        file_name = 'GOLDSTAR_' + datetime.now().strftime("%Y%m%d%H%M") + '.xlsx'
        workbook = xlsxwriter.Workbook(file_name)
        worksheet = workbook.add_worksheet('AMARK Export Report')
        bold = workbook.add_format({'bold': True})
        return bold, file_name, workbook, worksheet

    @staticmethod
    def send_email_with_attachment(attachment, self):
        template = self.env.ref('amgl.mmr_approval_complete', raise_if_not_found=True)
        mail_id = template.with_context(mmr_name='Export Report').send_mail(
            self.env.user.id,
            force_send=True,
            raise_exception=True,
            email_values={'attachment_ids': [attachment.id]}
        )
        return mail_id

    @staticmethod
    def add_file_in_attachment(file_name, self):
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
    def add_rows_in_worksheet(customers, row_count, self, worksheet):
        is_data_exists = False
        for customer in customers:
            mmr_list = self.env['amgl.metal_movement'].search([('customer', '=', customer.id)])
            customer_orders = self.env['amgl.order_line']. \
                search(['&', ('customer_id', '=', customer.id), ('state', '=', 'completed')])
            filtered_orders = []
            for customer_order in customer_orders:
                tomorrow = datetime.now().date() + timedelta(days=1)
                yesterday = datetime.now().date() + timedelta(days=-1)
                if datetime.strptime(customer_order.create_date,
                                     '%Y-%m-%d %H:%M:%S').date() < tomorrow and datetime.strptime(
                        customer_order.create_date, '%Y-%m-%d %H:%M:%S').date() > yesterday:
                    filtered_orders.append(customer_order)
            # transaction_description = ''
            # transaction_description_list = []
            # for mmr in mmr_list:
            #     transaction_description = transaction_description + mmr.mmt_name + ','
            #     order_id = 0
            #     for order_line in mmr.order_lines:
            #         order_id = order_line.id
            #         if not order_line.transaction_number:
            #             transaction_description = transaction_description + order_line.transaction_number + ','
            #     transaction_description = transaction_description + mmr.sepcial_instruction
            #     transaction_description_list.append({order_id: {
            #         'transaction_description': transaction_description
            #     }})
            column_count = 0
            if len(filtered_orders) > 0:
                is_data_exists = True
            for customer_order in filtered_orders:
                worksheet.write(row_count, column_count, customer.gst_account_number)
                column_count += 1
                worksheet.write(row_count, column_count, customer.full_name)
                column_count += 1
                worksheet.write(row_count, column_count, customer.account_number)
                column_count += 1
                worksheet.write(row_count, column_count, customer_order.create_date)
                column_count += 1
                worksheet.write(row_count, column_count, customer_order.transaction_number)
                column_count += 1
                worksheet.write(row_count, column_count, customer_order.transaction_type)
                column_count += 1
                worksheet.write(row_count, column_count, customer_order.products.product_code)
                column_count += 1
                worksheet.write(row_count, column_count, customer_order.total_received_quantity)
                column_count += 1
                worksheet.write(row_count, column_count, 'amark')
                column_count += 1
                worksheet.write(row_count, column_count, customer.amark_customer_code)
                column_count += 1
                # if len(transaction_description_list) > 0:
                #     if transaction_description_list[customer_order.id]:
                #         worksheet.write(row_count, column_count, transaction_description_list[customer_order.id])
                # else:
                worksheet.write(row_count, column_count, '')
                row_count += 1
                column_count = 0
        return is_data_exists

    @staticmethod
    def add_headers(bold, worksheet):
        worksheet.write('A1', 'gst_account_number', bold)
        worksheet.write('B1', 'customer_name', bold)
        worksheet.write('C1', 'amark_account_number', bold)
        worksheet.write('D1', 'transaction_date', bold)
        worksheet.write('E1', 'transaction_number', bold)
        worksheet.write('F1', 'transaction_type', bold)
        worksheet.write('G1', 'amark_precious_metal_code', bold)
        worksheet.write('H1', 'amark_quantity', bold)
        worksheet.write('I1', 'vault', bold)
        worksheet.write('J1', 'amark_customer_code', bold)
        worksheet.write('K1', 'transaction_description', bold)

    # </editor-fold>

    name = fields.Char(required=True)
    numberOfUpdates = fields.Integer('Number of Executions', help='The number of times the scheduler '
                                                                  'has run and sent email successfully')
    lastModified = fields.Date('Last Execution')
    mail_id = fields.Char()
    attachment_id = fields.Char()
