# -*- coding: utf-8 -*-

import base64
import uuid
from lxml import etree
from dateutil import parser
from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class MetalMovement(models.Model):
    _name = 'amgl.metal_movement'
    _description = 'Withdrawal'
    _order = 'create_date desc'
    _rec_name = 'mmr_number'

    @api.model
    def create(self, vals):

        self.update_customer_info_in_vals_object(vals)

        order_lines_from_request = self.get_order_lines_from_request_to_update_date(vals)

        self.check_transaction_fee(vals)

        self.check_if_product_exist_against_customer(order_lines_from_request)

        self.validate_quantity_create(order_lines_from_request)

        self.check_unique_package_number(vals)

        record = super(MetalMovement, self).create(vals)

        mmr_id = record['id']

        self.update_property_in_db('last_updated', self.env.user.id, mmr_id)

        first_letter_from_name, second_letter_from_name = self.get_first_letters_from_name(record)

        self.update_property_in_db('first_letter_from_name', first_letter_from_name, mmr_id, True)

        self.update_property_in_db('second_letter_from_name', second_letter_from_name, mmr_id, True)

        final_mmr_number = self.generate_mmr_number(record)

        self.update_property_in_db('mmr_number', final_mmr_number, mmr_id, True)

        record['show_vault_completed'] = True  # adding data into record directly because fields are stored False

        record['show_vault_review'] = True  # adding data into record directly because fields are stored False

        self.update_mmr_number(final_mmr_number, mmr_id)

        self.set_withdrawal_number(record)

        self.update_property_in_db('mmr_number', final_mmr_number, mmr_id, True)

        self.update_property_in_db('state', 'created', mmr_id, True)

        self.update_property_in_db('disable_custodian', True, mmr_id, False)

        self.send_approval_needed_email(record,
                                        final_mmr_number)  # sending MMR_Number in param because its updated in db but not in record object

        self.update_static_fields_in_order_line()

        return record

    def update_mmr_number(self, final_mmr_number, mmr_id):
        self.env.cr.execute(
            """ 
                update amgl_order_line 
                set  mmr_number = %s 
                where metal_movement_id in (select id from amgl_metal_movement where id = %s)""",
            [final_mmr_number, mmr_id])

    def check_transaction_fee(self, vals):
        transaction_fee = vals.get('customer_fees')
        if transaction_fee is not None and len(transaction_fee) > 0:
            for item in transaction_fee:
                transaction_fee_object = item[2]
                if transaction_fee_object:
                    customer_id = self.customer.id if self.customer else int(vals.get('customer'))
                    transaction_fee_object['customer_id'] = customer_id

    def check_if_product_exist_against_customer(self, order_lines_from_request):
        for order_line in order_lines_from_request:
            if hasattr(order_line, 'products'):
                order_lines = self.env['amgl.order_line'].search(
                    [('products', '=', order_line.products.id), ('is_master_records', '=', False)])
                for existing_order_line in order_lines:
                    if existing_order_line.customer_id != self.customer.id:
                        raise ValidationError("Selected product (" + str(
                            order_lines.products.goldstar_name) + ") doesn't exists against customer inventory.")

    def update_customer_info_in_vals_object(self, vals):
        if vals['customer']:
            customer_object = self.env['amgl.customer'].browse(vals['customer'])

            gst_account_number = customer_object.gst_account_number

            account_number = customer_object.account_number

            if customer_object:
                vals.update({
                    'mmf_account_number': gst_account_number if 'Gold' in str(
                        customer_object.custodian_id.name) else account_number,
                    'mmf_account_type': customer_object.account_type
                })

    @staticmethod
    def get_order_lines_from_request_to_update_date(vals):
        current_batch_number = uuid.uuid4()
        order_lines_from_request = vals.get('order_lines')
        if order_lines_from_request:
            for order_line_from_request in order_lines_from_request:
                if order_line_from_request[0] == 0:
                    order_line_from_request[2]['batch_number'] = current_batch_number
                order_line_from_request[2]['date_for_customer_metal_activitiy'] = vals.get('date_create')
        return order_lines_from_request

    def send_approval_needed_email(self, record, mmr_number):
        template = self.env.ref('amgl.create_mmr_email', raise_if_not_found=True)
        base_url = self.env['ir.config_parameter'].get_param('amgl.live.url')
        mmr_menu = self.env['ir.ui.menu'].search([('name', '=', 'Withdrawal')])
        mmr_windows_action = self.env['ir.actions.act_window'].search([('res_model', '=', 'amgl.metal_movement')],
                                                                      limit=1)
        temp_mmr_link = base_url + "/web#id=" + str(
            record['id']) + "&view_type=form&model=amgl.metal_movement&action=" + str(
            mmr_windows_action.id) + "&menu_id=" + str(mmr_menu.id)
        temp_mmr_name = "IRA Approval Needed"
        user_for_email = self.env['res.users'].search(
            ['|', ('id', '=', record['first_approve'].id), ('id', '=', record['second_approve'].id)])
        mmr_create_date = record['date_create']
        formated_mmr_date = str(datetime.strptime(mmr_create_date, '%Y-%m-%d').strftime("%m/%d/%Y"))
        additional_email_subject_info = self.get_additional_email_subject_info()
        email_cc = self.env['ir.config_parameter'].get_param('email.cc')
        for user_email in user_for_email:
            user = self.env['res.users'].search([('id', '=', user_email.id)], limit=1, order='id asc')
            template.with_context(approver_name=user.name,
                                  mmr_link=temp_mmr_link,
                                  mmr_number=str(mmr_number),
                                  date=formated_mmr_date,
                                  ref=str(record['reference']),
                                  fapprove=str(record['first_approve'].name),
                                  sapprove=str(record['second_approve'].name),
                                  customer=str(record['customer'].full_name),
                                  custodian=str(record['custodian'].name),
                                  mmt=str(record['metal_movement_type']),
                                  name=str(record['name']),
                                  additional_email_subject=str(additional_email_subject_info),
                                  mmf_accountnumber=str(record['mmf_account_number'] if record[
                                                                                            'mmf_account_number'] is not False else ''),
                                  mmf_accounttype=str(record['mmf_account_type']),
                                  mmt_name=str(record['mmt_name'] if record['mmt_name'] is not False else ''),
                                  mmt_address=str(record['mmt_address'] if record['mmt_address'] is not False else ''),
                                  mmt_account_number=str(record['mmt_account_number'] if record[
                                                                                             'mmt_account_number'] is not False else ''),
                                  to_email=user.login,
                                  email_cc=email_cc,
                                  mmr_name=temp_mmr_name).send_mail(
                user_email.id, force_send=False, raise_exception=True
            )

    def validate_quantity_from_inventory(self, record):
        for order in record['order_lines']:
            customer_master_product = self.env['amgl.order_line'].search([('customer_id', '=', record['customer'].id),
                                                                          ('state', '=', 'completed'),
                                                                          ('products', '=', order.products.id),
                                                                          ('is_master_records', '=', True)])
            if customer_master_product:
                print customer_master_product.id
                if float(order.quantity) <= customer_master_product.total_received_quantity:
                    result = customer_master_product.total_received_quantity - float(order.quantity)
                    # customer_master_product.write({'total_received_quantity': float(result)})
                    self.env.cr.execute("""
                    Update amgl_order_line set total_received_quantity = %s where id = %s """,
                                        [float(result), customer_master_product.id])
                else:
                    raise ValidationError(str(order.products.goldstar_name) + " quantity cannot be greater than " + str(
                        customer_master_product.total_received_quantity))
            else:
                raise ValidationError(str(order.products.goldstar_name) + " not available in the stock!")

    def get_additional_email_subject_info(self):
        base_url = self.env['ir.config_parameter'].get_param('amgl.live.url')
        subject = ''
        if 'irastorage' not in base_url:
            if 'localhost' in base_url:
                subject = '(Test: Localhost) '
            elif 'odev' in base_url:
                subject = '(Test: Odev) '
        return subject

    @staticmethod
    def generate_mmr_number(record):
        final_number = (str(record['id'])).zfill(5)
        final_mmr_number = 'W-' + str(final_number)
        return final_mmr_number

    @staticmethod
    def get_first_letters_from_name(record):
        if ' ' in record['first_approve'].name:
            first_letter_from_name = str(record['first_approve'].name.split(' ')[0][0]).capitalize() + str(
                record['first_approve'].name.split(' ')[1][0]).capitalize()
            second_letter_from_name = str(record['second_approve'].name.split(' ')[0][0]).capitalize() + str(
                record['second_approve'].name.split(' ')[1][0]).capitalize()
        else:
            first_letter_from_name = str(record['first_approve'].name[0]).capitalize()
            second_letter_from_name = ''
        return first_letter_from_name, second_letter_from_name

    def update_property_in_db(self, column_to_update, value_to_update, record_id_to_update,
                              send_value_in_quotation=False):
        if send_value_in_quotation:
            self.env.cr.execute(
                "Update amgl_metal_movement set " + column_to_update + " = '" + str(
                    value_to_update) + "' where id =" + str(
                    record_id_to_update))
        else:
            self.env.cr.execute(
                'Update amgl_metal_movement set ' + column_to_update + '=' + str(value_to_update) + ' where id =' + str(
                    record_id_to_update))

    @staticmethod
    def validate_quantity_create(order_lines):
        if not order_lines:
            raise ValidationError("Please enter data in 'Metals To Be Moved' section to create withdrawal request!")
        for order_line in order_lines:
            _current_order_line = order_line[2]
            if _current_order_line and _current_order_line['quantity']:
                _quantity = _current_order_line['quantity']
                try:
                    _qty = int(_quantity)
                except:
                    raise ValidationError("Quantity must be integer.")
                if int(_quantity) <= 0:
                    raise ValidationError("Quantity cannot be less than 1.")
            else:
                raise ValidationError("Quantity must be something.")

    def check_unique_package_number(self, vals):
        all_packages_text = []
        all_packages_text_after_false_removal = []
        num_of_packages = vals.get('number_of_packages')
        if not num_of_packages:
            num_of_packages = self.number_of_packages
        for number in range(0, int(num_of_packages)):
            package_number = 'package' + str(number + 1)
            current_package = vals.get(package_number)  # type: object
            if current_package is not None and current_package:
                all_packages_text.append(vals.get(package_number))
            elif current_package:
                all_packages_text.append(self[package_number])

        for item in all_packages_text:
            if item:
                all_packages_text_after_false_removal.append(item)

        if len(all_packages_text_after_false_removal) != len(set(all_packages_text_after_false_removal)):
            raise ValidationError('Duplicate Package Tracking Number are not allowed')

    def set_withdrawal_number(self, record):
        new_batch_number = 'W-' + (str(record['id'])).zfill(5)
        self.env.cr.execute(
            "Update amgl_order_line set batch_number = '" + str(
                new_batch_number) + "' Where metal_movement_id = " + str(
                record['id']))

    @staticmethod
    def validate_quantity_write(order_lines):
        if order_lines:
            _total_order_lines = 0
            for item in order_lines:
                _order_line_state = item[
                    0]  # item[0] usually contains values like 1,2,3 represents the state of object whether its in update,create or delete
                if (not item[
                    2]) and _order_line_state == 2:  # Count removed order lines to check if all order lines are removed
                    _total_order_lines += 1
            if _total_order_lines == len(order_lines):
                raise ValidationError("Please enter data in 'Metals To Be Moved' section to create withdrawal request!")

    @api.multi
    def write(self, vals):
        if self.state is False:
            record = super(MetalMovement, self).write(vals)
        else:

            order_lines = vals.get('order_lines')

            customer = vals.get('customer')

            self.check_transaction_fee(vals)

            self.update_boolean_fields_again_vault_complete_and_review(
                vals)  # updating boolean fields based on vault review and vault complete dropdown values.

            self.check_unique_package_number(vals)  # check package tracking number.

            if 'date_create' in vals:
                self.update_date_for_customer_metal_activity(
                    vals)  # updating date_for_customer_metal_activity in order_line for current metal activity.

            self.validate_quantity_write(order_lines)  # check and validate quantity against product.

            if order_lines:
                self.validate_product(vals, order_lines)  # check if product exist and exist against current customer.

            if customer:
                self.update_customer_info_in_vals_object(vals)

            record = super(MetalMovement, self).write(vals)

            if not self.is_first_approve and not self.is_second_approve and not self.is_rejected:
                self.send_ira_approval_needed_email()

            if self.is_rejected:
                self.send_revised_approval_needed_email()

            if self.vault_complete and self.vault_review and self.is_complete == False and self.check_packages_content() and self.is_first_approve and self.is_second_approve:
                self.send_mmr_complete_email()

        self.update_static_fields_in_order_line()

        return record

    def update_boolean_fields_again_vault_complete_and_review(self, vals):
        if 'vault_complete' in vals:
            vals['vault_complete_added_by'] = self.env.user.id
            vals['last_updated'] = self.env.user.id
            vals['v_complete'] = True
        if 'vault_review' in vals:
            vals['vault_review_added_by'] = self.env.user.id
            vals['last_updated'] = self.env.user.id
            vals['v_review'] = True

    def update_static_fields_in_order_line(self):
        self.env.cr.execute("""UPDATE amgl_order_line 
                                            SET transaction_detail_sort_date = date_received
                                            WHERE metal_movement_id is null""")
        self.env.cr.execute("""
                    UPDATE amgl_order_line b
                    SET transaction_detail_sort_date = a.date_create
                    FROM amgl_metal_movement AS a
                    WHERE a.id = b.metal_movement_id;
                """)

    def send_mmr_complete_email(self):

        template = self.env.ref('amgl.mmr_approval_total_complete', raise_if_not_found=True)

        mmr_object = self.env['amgl.metal_movement'].search([('id', '=', self.id)])

        if len(self.customer_fees) > 0:

            self.update_state_completed_on_current_mmr()

            attachment_id = self.generate_report_and_get_attachement_id()

            email_subject = 'Acct #' + (
                mmr_object.customer.account_number if 'Gold' not in mmr_object.custodian.name
                else mmr_object.customer.gst_account_number) + ' Withdrawal Complete'

            additional_email_subject_info = self.get_additional_email_subject_info()

            if additional_email_subject_info:
                email_subject = additional_email_subject_info + email_subject

            email_cc = self.env['ir.config_parameter'].get_param('email.cc')

            emails = self.get_email_for_withdrawal_complete(self.custodian.name)

            mail_id = template.with_context(
                custodian_name=mmr_object.custodian.name,
                mmr_number=mmr_object.mmr_number,
                email_subject=email_subject,
                email_cc=email_cc,
                email_to=emails
            ).send_mail(1, force_send=False, raise_exception=True, email_values={'attachment_ids': [attachment_id]})

    def get_email_for_withdrawal_complete(self, cust_name):
        email_groups = self.env['amgl.email.group'].search([])
        emails = ''
        for item in email_groups:
            if cust_name in item.name:  # send emails to custodian group
                emails += ',' + item.emails

            if 'Vault Group' in item.name:  # send emails to vault group
                emails += ',' + item.emails

            if 'Headquarter' in item.name:  # send emails to Headquarter group
                emails += ',' + item.emails

        emails = emails.lstrip(",")
        emails = emails.rstrip(",")
        return emails

    def update_state_completed_on_current_mmr(self):
        self.env.cr.execute(
            "UPDATE amgl_metal_movement SET is_complete =  True,state = 'completed' WHERE id=%s ", [self.id])

    def generate_report_and_get_attachement_id(self):
        report_result = self.env['report'].get_pdf(self.ids, 'amgl.report_metalmovement_complete', data={
            'ids': self.ids,
            'model': 'amgl.metal_movement',
            'form': self.ids
        })
        attachment_id = self.add_report_to_attachment(report_result, self.mmr_number + '.pdf')
        return attachment_id

    def send_revised_approval_needed_email(self):
        template = self.env.ref('amgl.revised_mmr_email', raise_if_not_found=True)
        base_url = self.env['ir.config_parameter'].get_param('amgl.live.url')
        mmr_menu = self.env['ir.ui.menu'].search([('name', '=', 'Withdrawal')])
        mmr_windows_action = self.env['ir.actions.act_window'].search([('res_model', '=', 'amgl.metal_movement')],
                                                                      limit=1)
        temp_mmr_link = base_url + "/web#id=" + str(
            self.id) + "&view_type=form&model=amgl.metal_movement&action=" + str(
            mmr_windows_action.id) + "&menu_id=" + str(mmr_menu.id)
        temp_mmr_name = "Revised Approval Needed"
        user_for_email = self.env['res.users'].search(
            ['|', ('id', '=', self.first_approve.id), ('id', '=', self.second_approve.id)])
        additional_email_subject_info = self.get_additional_email_subject_info()
        email_cc = self.env['ir.config_parameter'].get_param('email.cc')
        for user_email in user_for_email:
            user = self.env['res.users'].search([('id', '=', user_email.id)])
            template.with_context(approver_name=user.name,
                                  mmr_number=self.mmr_number,
                                  mmr_link=temp_mmr_link,
                                  email=user.login,
                                  additional_email_subject=str(additional_email_subject_info),
                                  mmr_name=temp_mmr_name,
                                  email_cc=email_cc).send_mail(
                user_email.id, force_send=False, raise_exception=True
            )
        self.update_property_in_db('is_rejected', False, self.id)
        self.update_property_in_db('state', 'created', self.id, True)

    def send_ira_approval_needed_email(self):
        template = self.env.ref('amgl.create_mmr_email', raise_if_not_found=True)
        base_url = self.env['ir.config_parameter'].get_param('amgl.live.url')
        mmr_menu = self.env['ir.ui.menu'].search([('name', '=', 'Withdrawal')])
        mmr_windows_action = self.env['ir.actions.act_window'].search([('res_model', '=', 'amgl.metal_movement')],
                                                                      limit=1)
        temp_mmr_link = base_url + "/web#id=" + str(self.id) + "&view_type=form&model=amgl.metal_movement&action=" + \
                        str(mmr_windows_action.id) + "&menu_id=" + str(mmr_menu.id)
        temp_mmr_name = "IRA Approval Needed"
        user_for_email = self.env['res.users'].search(
            ['|', ('id', '=', self.first_approve.id), ('id', '=', self.second_approve.id)])
        mmr_create_date = self.date_create
        formated_mmr_date = str(datetime.strptime(mmr_create_date, '%Y-%m-%d').strftime("%m/%d/%Y"))
        additional_email_subject_info = self.get_additional_email_subject_info()
        email_cc = self.env['ir.config_parameter'].get_param('email.cc')
        for user_email in user_for_email:
            user = self.env['res.users'].search([('id', '=', user_email.id)], limit=1, order='id asc')
            template.with_context(approver_name=user.name,
                                  mmr_link=temp_mmr_link,
                                  mmr_number=str(self.mmr_number),
                                  date=formated_mmr_date,
                                  ref=str(self.reference),
                                  fapprove=str(self.first_approve.name),
                                  sapprove=str(self.second_approve.name),
                                  customer=str(self.customer.full_name),
                                  custodian=str(self.custodian.name),
                                  mmt=str(self.metal_movement_type),
                                  name=str(self.name),
                                  additional_email_subject=str(additional_email_subject_info),
                                  mmf_accountnumber=str(
                                      self.mmf_account_number if self.mmf_account_number is not False else ''),
                                  mmf_accounttype=str(self.mmf_account_type),
                                  mmt_name=str(self.mmt_name if self.mmt_name is not False else ''),
                                  mmt_address=str(self.mmt_address if self.mmt_address is not False else ''),
                                  mmt_account_number=str(
                                      self.mmt_account_number if self.mmt_account_number is not False else ''),
                                  to_email=user.login,
                                  mmr_name=temp_mmr_name,
                                  email_cc=email_cc).send_mail(
                user_email.id, force_send=False, raise_exception=True
            )

    def validate_product(self, vals, order_lines):
        if order_lines:
            for order_line in order_lines:
                product_id = 0
                if hasattr(order_line, 'products'):
                    product_id = order_line.products.id
                else:
                    if order_line[2]:
                        try:
                            product_id = int(order_line[2]['products'])
                        except:
                            pass
                        if product_id is not 0:
                            current_customer = self.customer.id
                            updated_customer = vals.get('customer')
                            if updated_customer:
                                current_customer = updated_customer
                            existing_order_lines = self.env['amgl.order_line'].search(
                                [('products', '=', product_id), ('is_master_records', '=', False),
                                 ('customer_id', '=', current_customer)])
                            product_to_show_message = self.env['amgl.products'].search([('id', '=', product_id)])
                            if len(existing_order_lines) == 0:
                                raise ValidationError("Selected product (" + str(product_to_show_message[
                                                                                     0].goldstar_name) + ") doesn't exists against customer inventory.")
                    else:
                        continue

    def update_date_for_customer_metal_activity(self, vals):
        self.env.cr.execute(
            "update amgl_order_line set  date_for_customer_metal_activitiy = '" + vals.get(
                'date_create') + "' where metal_movement_id = " + str(self.id))

    def check_packages_content(self):
        _allPackages = [self.package1, self.package2, self.package3, self.package4, self.package5, self.package6,
                        self.package7,
                        self.package8, self.package9, self.package10, self.package11, self.package12, self.package13,
                        self.package14,
                        self.package15, self.package16, self.package17, self.package18, self.package19, self.package20]
        _numberOfPackages = int(self.number_of_packages)
        _packagesToBeChecked = _allPackages[:_numberOfPackages]
        for package in _packagesToBeChecked:
            if not package:
                return False
        return True

    def update_approve(self):
        if self.env.user.id == self.first_approve.id:
            self.update({
                'is_first_approve': True
            })
        if self.env.user.id == self.second_approve.id:
            self.update({
                'is_second_approve': True
            })
        if self.env.user.id == self.first_approve.id or self.env.user.id == self.second_approve.id:
            self.update({
                'state': 'in_progress'
            })
        if self.is_first_approve and self.is_second_approve:
            mmr = self.ids
            data_object = {
                'ids': mmr,
                'model': 'amgl.metal_movement',
                'form': mmr
            }
            template = self.env.ref('amgl.mmr_approval_complete', raise_if_not_found=True)
            mmr_object = self.env['amgl.metal_movement'].search([('id', '=', self.id)])
            base_url = self.env['ir.config_parameter'].get_param('amgl.live.url')
            mmr_menu = self.env['ir.ui.menu'].search([('name', '=', 'Withdrawal')])
            mmr_windows_action = self.env['ir.actions.act_window'].search([('res_model', '=', 'amgl.metal_movement')],
                                                                          limit=1)
            temp_mmr_link = base_url + "/web#id=" + str(
                mmr_object.id) + "&view_type=form&model=amgl.metal_movement&action=" + str(
                mmr_windows_action.id) + "&menu_id=" + str(mmr_menu.id)
            report_result = self.env['report'].get_pdf(mmr, 'amgl.report_metalmovement', data=data_object)
            attachment_id = self.add_report_to_attachment(report_result,
                                                          'Withdrawal Request ' + self.mmr_number + '.pdf')
            additional_email_subject_info = self.get_additional_email_subject_info()
            user_groups = ['Administrator', 'Sub-Admins']
            user_for_email = self.get_users_for_email(user_groups)

            emails = ''
            for item in user_for_email:
                emails += ',' + item[2]

            emails = self.get_email_for_vault_group(emails)
            emails = emails.lstrip(",")
            emails = emails.rstrip(",")

            email_cc = self.env['ir.config_parameter'].get_param('email.cc')

            mail_id = template.with_context(
                custodian_name=mmr_object.custodian.name,
                mmr_number=mmr_object.mmr_number,
                mmr_name="Withdrawal Approved # " + self.mmr_number,
                additional_email_subject=str(additional_email_subject_info),
                mmr_link=temp_mmr_link,
                email_cc=email_cc,
                email_to=emails
            ).send_mail(1, force_send=False, raise_exception=True,
                        email_values={'attachment_ids': [attachment_id]})

        base_url = self.env['ir.config_parameter'].get_param('amgl.live.url')
        return {
            'type': 'ir.actions.act_url',
            'url': str(base_url) + '/amgl/static/html/approval_accpeted.html',
            'target': 'self'
        }

    def get_email_for_vault_group(self, emails):
        email_groups = self.env['amgl.email.group'].search([])
        for item in email_groups:
            if 'Vault Group' in item.name:  # send emails to Vault group
                emails += ',' + item.emails

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

    def add_report_to_attachment(self, report_result, report_name):
        attachment = self.env['ir.attachment'].create({'name': report_name,
                                                       'datas': base64.b64encode(report_result),
                                                       'datas_fname': report_name,
                                                       'res_model': 'res.users',
                                                       'res_id': 1, })
        return attachment.id

    def cancel_request(self):
        mmr_object = self.env['amgl.metal_movement'].search([('id', '=', self.id)])
        mmr_object.write({'state': 'cancel'})
        for order in mmr_object.order_lines:
            order.write({'quantity': '0'})
            customer_master_product = self.env['amgl.order_line'].search([('customer_id', '=', mmr_object.customer.id),
                                                                          ('state', '=', 'completed'),
                                                                          ('products', '=', order.products.id),
                                                                          ('is_master_records', '=', True)])
            if customer_master_product:
                result = customer_master_product.total_received_quantity + float(order.quantity)
                customer_master_product.write({'total_received_quantity': float(result)})

        return True

    def _get_current_user(self):
        if self.is_rejected:
            self.update({'current_user': False})
        elif self.first_approve == self.env.user:
            if self.is_first_approve:
                self.update({'current_user': False})
            else:
                self.update({'current_user': True})  # sending false because we need to show in True case
        elif self.second_approve == self.env.user:
            if self.is_second_approve:
                self.update({'current_user': False})
            else:
                self.update({'current_user': True})
        else:
            self.update({'current_user': False})
        return True

    def _get_review_complete_user(self):
        if self.vault_review == self.env.user:
            if self.v_review:
                self.update({'request_review_user': False})
            else:
                self.update({'request_review_user': True})
        elif self.vault_complete == self.env.user:
            if self.v_complete:
                self.update({'request_complete_user': False})
            else:
                self.update({'request_complete_user': True})
        return True

    @api.onchange('customer')
    def onchange_customer(self):
        if self.customer and self.custodian:
            if self.customer.custodian_id.name != self.custodian.name:
                raise ValidationError(
                    self.customer.full_name + " doesn't belong to " + self.custodian.name + ", Please select another customer.")
        account_number = self.customer.account_number
        if 'Gold' in str(self.custodian.display_name):
            account_number = self.customer.gst_account_number

        self.update({
            'mmf_account_number': account_number,
            'mmf_account_type': self.customer.account_type
        })
        self.order_lines = []
        self.customer_fees = []
        self.grace_period_validation = ''
        if self.customer.customer_order_lines and self.customer.grace_period:
            temp_end_of_period = parser.parse(self.customer.customer_order_lines[0].date_received) + relativedelta(
                months=self.customer.grace_period)
            end_of_period = parser.parse(str(temp_end_of_period)).date()
            today_date = datetime.now().date()
            if today_date <= end_of_period:
                self.grace_period_validation = 'Selected customer is under `No Fee Duration` and ' + \
                                               str(end_of_period - today_date).split(',')[
                                                   0] + ' are remaining. Please add transaction fees accordingly !'
            else:
                self.grace_period_validation = ''

    @api.onchange('custodian')
    def on_change_custodian(self):
        if self.custodian:
            self.env.cr.execute("""
                    SELECT c.id
                    FROM amgl_customer c
                    INNER JOIN amgl_order_line o ON o.customer_id = c.id
                    INNER JOIN amgl_custodian cu ON cu.id = c.custodian_id
                    WHERE c.custodian_id = """ + str(self.custodian.id) + """
                        AND (c.is_account_closed = False or c.is_account_closed is Null)
                        AND o.total_received_quantity > 0
                        AND o.is_master_records = True
                """)  # Query to fetch all customers associated to selected custodian.
            customers_ids = self.env.cr.fetchall()
            customers = self.env['amgl.customer'].search([('id', 'in', customers_ids)])
            filtered_customers = []
            self.filter_customers_for_grace_period(customers, filtered_customers)
            self.customer = []
            self.order_lines = []
            self.customer_fees = []
            return {'domain': {'customer': [('id', 'in', filtered_customers)]}}

    def filter_customers_for_grace_period(self, customers, filtered_customers):
        for item in customers:
            if item.grace_period:
                customer_order_lines = self.env['amgl.order_line'].search(
                    ['&', ('customer_id', '=', item.id), ('is_master_records', '=', False)],
                    order='date_received asc')
                first_deposit_date = customer_order_lines[0].date_received
                end_of_grace_period = parser.parse(first_deposit_date) + relativedelta(
                    months=item.grace_period)
                today_date = datetime.now()
                if today_date > end_of_grace_period:
                    filtered_customers.append(item.id)
            else:
                filtered_customers.append(item.id)

    @api.depends('custodian', 'customer', 'date_create', 'reference', 'first_approve', 'second_approve', 'mmt_name')
    def check_custodian(self):
        if self.custodian and self.customer and self.date_create \
                and self.reference and self.first_approve and self.second_approve and self.mmt_name:
            self.is_o2m = True

    @api.multi
    def check_special_instruction(self):
        if self.special_instruction:
            if self.special_instruction.encode('ascii', 'ignore') == '<p><br></p>':
                self.update({
                    'is_special_instruction_available': False
                })
            else:
                self.update({
                    'is_special_instruction_available': True
                })
        else:
            self.update({
                'is_special_instruction_available': False
            })

    @api.onchange('metal_movement_type')
    def mmr_type_change(self):
        # Removing all customer fees already was there in MMR on change of MMR type
        if len(self.customer_fees) > 0:
            return {'value': {'customer_fees': []}}

    @api.onchange('number_of_packages')
    def on_change_packages(self):
        if self.number_of_packages:
            self.customer_fees = []  # Removing all customer fees already was there in MMR on change of number_of_packages
            _numberOfPackages = int(self.number_of_packages)
            for i in range(0, _numberOfPackages):
                self['p' + str(i + 1) + '_boolean'] = True
            for k in range(_numberOfPackages, 20):
                self['p' + str(k + 1) + '_boolean'] = False
                self['package' + str(k + 1)] = ''

    def launch_rejection_wizard(self):
        return {
            'name': 'Rejection Reason',
            'type': 'ir.actions.act_window',
            'res_model': 'amgl.reject_wizard',
            'src_model': 'amgl.metal_movement',
            'view_mode': 'form',
            'target': 'new'
        }

    @api.multi
    def unlink(self):
        for mmr in self:
            self.restrict_removal_incase_of_completed_withdrawal(mmr)

        for item in self:
            mmr_object = self.set_mmr_state_to_cancel(item)

            for order in mmr_object.order_lines:
                self.update_related_orderlines_states_with_quantity(mmr_object, order)

        for mmr in self:
            self.remove_all_associated_transaction_fees(mmr)

        return super(MetalMovement, self).unlink()

    def remove_all_associated_transaction_fees(self, mmr):
        transaction_fees = self.env['amgl.fees'].search([('metal_movement_id', '=', mmr.id)])
        for item in transaction_fees:
            self.env.cr.execute('DELETE FROM amgl_fees where id = ' + str(item.id))

    def update_related_orderlines_states_with_quantity(self, mmr_object, order):
        customer_master_product = self.env['amgl.order_line'].search(
            [('customer_id', '=', mmr_object.customer.id),
             ('products', '=', order.products.id),
             ('is_master_records', '=', True)])
        if customer_master_product:
            result = customer_master_product.total_received_quantity + float(order.quantity)
            customer_master_product.write({'total_received_quantity': float(result)})
            self.env.cr.execute('UPDATE amgl_order_line SET is_active = False where id = ' + str(order.id))
        order_lines_associated_with_mmr = self.env['amgl.order_line'].search(
            [('customer_id', '=', mmr_object.customer.id),
             ('products', '=', order.products.id),
             ('is_master_records', '=', False), ('metal_movement_id', '=', mmr_object.id)])
        for item in order_lines_associated_with_mmr:
            self.env.cr.execute('Delete from amgl_order_line where id = ' + str(item.id))

    def set_mmr_state_to_cancel(self, item):
        mmr_object = self.env['amgl.metal_movement'].search([('id', '=', item.id)])
        self.update_property_in_db('state', 'cancel', mmr_object.id, True)
        return mmr_object

    @staticmethod
    def restrict_removal_incase_of_completed_withdrawal(mmr):
        if mmr.state == 'completed':
            raise ValidationError("You have selected completed Withdrawal which cannot be deleted.")

    def mmr_review(self):
        if self.is_first_approve:
            if self.is_second_approve:
                if self.env.user.id == self.vault_review.id:
                    self.update({
                        'v_review': True
                    })
            else:
                raise ValidationError("Withdrawal Request is in process, It is not yet approved by "
                                      "second authorizer " + str(self.second_approve.name))
        else:
            raise ValidationError("Withdrawal Request is in process, It is not yet approved by "
                                  "first authorizer " + str(self.first_approve.name))
        return True

    def mmr_completed(self):
        if self.is_first_approve:
            if self.is_second_approve:
                if self.v_review:
                    if self.env.user.id == self.vault_complete.id:
                        self.update({
                            'v_complete': True,
                            'state': 'completed'
                        })
                else:
                    raise ValidationError("Withdrawal Request is in process, It is not yet reviewed by "
                                          "vault " + str(self.vault_review.name))
            else:
                raise ValidationError("Withdrawal Request is in process, It is not yet approved by "
                                      "second authorizer " + str(self.second_approve.name))
        else:
            raise ValidationError("Withdrawal Request is in process, It is not yet approved by "
                                  "first authorizer " + str(self.first_approve.name))
        return True

    def _get_current_user_role(self):
        if self.env.user.has_group('amgl.group_amark_admins'):
            self.update({'user_role': 'Admin'})
        if self.env.user.has_group('amgl.group_amark_custodian'):
            self.update({'user_role': 'Custodian'})
        if self.env.user.has_group('amgl.group_amark_sub_admins'):
            self.update({'user_role': 'SubAdmin'})
        if self.env.user.has_group('amgl.group_amark_vault'):
            self.update({'user_role': 'Vault'})

    @api.onchange('vault_review')
    def _onchange_vault_review(self):
        if self.vault_review:
            object = self.env['amgl.metal_movement'].search([('id', '=', self._origin.id)])
            self.vault_review_added_by = self.env.user.id
            if ' ' in self.vault_review.name:
                two_letters_for_reviewed = str(self.vault_review.name.split(' ')[0][0]).capitalize() + \
                                           str(self.vault_review.name.split(' ')[1][0]).capitalize()
                self.update_property_in_db('two_letters_for_reviewed', two_letters_for_reviewed, self._origin.id,
                                           True)
            else:
                self.update_property_in_db('two_letters_for_reviewed', str(self.vault_review.name[0]).capitalize(),
                                           self._origin.id, True)

            if self.env.user.has_group('amgl.group_amark_admins'):
                self.vault_review_added_by = self.env.user.id
                self.show_vault_completed = True
            else:
                self.vault_review_added_by = self.env.user.id
                self.show_vault_completed = False

    @api.onchange('vault_complete')
    def _onchange_vault_complete(self):
        if self.vault_complete:
            if ' ' in self.vault_complete.name:
                two_letters_for_completed = str(self.vault_complete.name.split(' ')[0][0]).capitalize() + \
                                            str(self.vault_complete.name.split(' ')[1][0]).capitalize()
                self.update_property_in_db('two_letters_for_completed', two_letters_for_completed, self._origin.id,
                                           True)
            else:
                self.update_property_in_db('two_letters_for_completed', str(self.vault_complete.name[0]).capitalize(),
                                           self._origin.id, True)
            if self.env.user.has_group('amgl.group_amark_admins'):
                self.vault_complete_added_by = self.env.user.id
                self.show_vault_review = True
            else:
                self.vault_complete_added_by = self.env.user.id
                self.show_vault_review = False

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(MetalMovement, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(res['arch'])
        for node_form in doc.xpath("//form"):
            if self.env.user.has_group('amgl.group_amark_authorizer'):
                node_form.attrib['create'] = '0'
                node_form.attrib['edit'] = '0'
            res['arch'] = etree.tostring(doc)
        return res

    def _get_show_vault_dropdown(self):
        for item in self:
            if self.env.user.has_group('amgl.group_amark_admins'):
                if self.is_first_approve and self.is_second_approve:
                    item.show_vault_completed = True
                    item.show_vault_review = True
            else:
                if self.is_first_approve and self.is_second_approve:
                    if item.vault_review:
                        item.show_vault_completed = True
                        item.show_vault_review = False
                    if item.vault_complete:
                        item.show_vault_review = True
                        item.show_vault_completed = False
                    if not item.vault_review and not item.vault_complete:
                        item.show_vault_completed = True
                        item.show_vault_review = True

                if self.is_first_approve is False or self.is_second_approve is False:
                    item.show_vault_completed = False
                    item.show_vault_review = False

                if item.last_updated.id == self.env.user.id:
                    if item.vault_complete:
                        item.show_vault_review = False
                    elif item.vault_review:
                        item.show_vault_completed = False
                    else:
                        item.show_vault_completed = False
                        item.show_vault_review = False

    @staticmethod
    def set_visibility_for_vault(item):
        if item.vault_complete:
            item.show_vault_completed = False
        else:
            item.show_vault_completed = True

        if item.vault_review:
            item.show_vault_review = False
        else:
            item.show_vault_review = True

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        operator = 'ilike'
        limit = 100
        _input = ''
        _isFromFilter = False
        for item in args:
            if 'mmr_number' in item:
                _input = item[2]
                _isFromFilter = False
            elif 'mmr_number' not in item:
                _isFromFilter = True
        if not _isFromFilter:
            if len(args) > 1:
                del args[1]
                args.append(u'|')
                args.append(u'|')
                args.append(u'|')
                mmr_number = ['mmr_number', 'ilike', _input]
                args.append(map(unicode, mmr_number))
                customer = ['customer', 'ilike', _input]
                args.append(map(unicode, customer))
                first_approve = ['first_approve', 'ilike', _input]
                args.append(map(unicode, first_approve))
                second_approve = ['second_approve', 'ilike', _input]
                args.append(map(unicode, second_approve))
        return super(MetalMovement, self).search(args, offset=offset, limit=limit, order=order, count=count)

    name = fields.Char()
    date_create = fields.Date(string="Date", required=True)
    reference = fields.Char(string="Reference", required=True)
    is_first_approve = fields.Boolean()
    is_o2m = fields.Boolean(compute="check_custodian")
    is_second_approve = fields.Boolean()
    is_complete = fields.Boolean()
    v_review = fields.Boolean()
    v_complete = fields.Boolean()
    current_user = fields.Boolean(compute='_get_current_user')
    request_review_user = fields.Boolean(compute='_get_review_complete_user')
    request_complete_user = fields.Boolean(compute='_get_review_complete_user')
    first_approve = fields.Many2one("res.users", string="First Approve By", required=True)
    second_approve = fields.Many2one("res.users", string="Second Approve By", required=True)
    vault_review = fields.Many2one("amgl.review_users", string="Vault Review")
    vault_complete = fields.Many2one("amgl.review_users", string="Vault Completed")
    show_vault_review = fields.Boolean(compute=_get_show_vault_dropdown, store=False)
    show_vault_completed = fields.Boolean(compute=_get_show_vault_dropdown, store=False)
    vault_review_added_by = fields.Many2one('res.users')
    vault_complete_added_by = fields.Many2one('res.users')
    special_instruction = fields.Html(string="Special Instruction")
    metal_movement_type = fields.Selection(selection=[
            ('IT', 'Internal Transfer')
        ,('USPSPRI', 'USPS Priority Mail')
        ,('UPS2D', 'UPS 2nd Day')
        ,('UPSND', 'UPS Next Day')
        ,('OTHER', 'Other')
        ,('TRANSAC', 'Armored Carrier')
        ,('PICKUP', 'InPerson Pickup')] , default="IT", required=True)
    custodian = fields.Many2one("amgl.custodian", string="Custodian", required=True)
    customer = fields.Many2one("amgl.customer", string="Customer", required=True)
    mmf_account_number = fields.Char(string="Account Number", readonly=True, store=True)
    mmf_account_type = fields.Selection(selection=[('Commingled', 'Commingled'), ('Segregated', 'Segregated')]
                                        , string="Account Type", readonly=True, store=True)
    mmt_name = fields.Char(string="Name", required=True)
    mmt_address = fields.Char(string="Address")
    mmt_account_number = fields.Char(string="Account # (if applicable)")
    mmt_company = fields.Char(string="Company")
    pickup_date = fields.Datetime(string="Pickup Datetime")
    rejection_reason = fields.Html('Rejection Reason')
    order_lines = fields.One2many('amgl.order_line', 'metal_movement_id', string=' ')
    state = fields.Selection([('created', 'Created'), ('in_progress', 'In Progress'),
                              ('approved', 'Approved'), ('rejected', 'Rejected'), ('reviewed', 'Reviewed'),
                              ('completed', 'Completed'), ('cancel', 'Cancelled'),
                              ('vault_completed', 'Vault Completed')], 'Status',
                             readonly=True)
    number_of_packages = fields.Selection(selection=[('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'),
                                                     ('6', '6'), ('7', '7'), ('8', '8'), ('9', '9'), ('10', '10'),
                                                     ('11', '11'), ('12', '12'), ('13', '13'), ('14', '14'),
                                                     ('15', '15'), ('16', '16'), ('17', '17'), ('18', '18'),
                                                     ('19', '19'), ('20', '20')], string='Total Number of Packages',
                                          default='1')
    package1 = fields.Char(string='Package 1', invisible=True)
    package2 = fields.Char(string='Package 2', invisible=True)
    package3 = fields.Char(string='Package 3', invisible=True)
    package4 = fields.Char(string='Package 4', invisible=True)
    package5 = fields.Char(string='Package 5', invisible=True)
    package6 = fields.Char(string='Package 6', invisible=True)
    package7 = fields.Char(string='Package 7', invisible=True)
    package8 = fields.Char(string='Package 8', invisible=True)
    package9 = fields.Char(string='Package 9', invisible=True)
    package10 = fields.Char(string='Package 10', invisible=True)
    package11 = fields.Char(string='Package 11', invisible=True)
    package12 = fields.Char(string='Package 12', invisible=True)
    package13 = fields.Char(string='Package 13', invisible=True)
    package14 = fields.Char(string='Package 14', invisible=True)
    package15 = fields.Char(string='Package 15', invisible=True)
    package16 = fields.Char(string='Package 16', invisible=True)
    package17 = fields.Char(string='Package 17', invisible=True)
    package18 = fields.Char(string='Package 18', invisible=True)
    package19 = fields.Char(string='Package 19', invisible=True)
    package20 = fields.Char(string='Package 20', invisible=True)
    p1_boolean = fields.Boolean(string='P1 Boolean')
    p2_boolean = fields.Boolean(string='P2 Boolean')
    p3_boolean = fields.Boolean(string='P3 Boolean')
    p4_boolean = fields.Boolean(string='P4 Boolean')
    p5_boolean = fields.Boolean(string='P5 Boolean')
    p6_boolean = fields.Boolean(string='P6 Boolean')
    p7_boolean = fields.Boolean(string='P7 Boolean')
    p8_boolean = fields.Boolean(string='P8 Boolean')
    p9_boolean = fields.Boolean(string='P9 Boolean')
    p10_boolean = fields.Boolean(string='P10 Boolean')
    p11_boolean = fields.Boolean(string='P11 Boolean')
    p12_boolean = fields.Boolean(string='P12 Boolean')
    p13_boolean = fields.Boolean(string='P13 Boolean')
    p14_boolean = fields.Boolean(string='P14 Boolean')
    p15_boolean = fields.Boolean(string='P15 Boolean')
    p16_boolean = fields.Boolean(string='P16 Boolean')
    p17_boolean = fields.Boolean(string='P17 Boolean')
    p18_boolean = fields.Boolean(string='P18 Boolean')
    p19_boolean = fields.Boolean(string='P19 Boolean')
    p20_boolean = fields.Boolean(string='P20 Boolean')
    customer_fees = fields.One2many('amgl.fees', 'metal_movement_id', string='Fees')
    is_reminder_sent = fields.Boolean(default=False)
    user_role = fields.Char(compute=_get_current_user_role)
    mmr_number = fields.Char(string="Withdrawal # ")
    first_letter_from_name = fields.Char()
    second_letter_from_name = fields.Char()
    two_letters_for_completed = fields.Char()
    two_letters_for_reviewed = fields.Char()
    is_rejected = fields.Boolean(default=False)
    last_updated = fields.Many2one("res.users", string="Last Updated", store=True)
    is_special_instruction_available = fields.Boolean(compute="check_special_instruction")
    reminder_sent_date = fields.Datetime()
    disable_custodian = fields.Boolean(default=False)
    grace_period_validation = fields.Char(default='')
