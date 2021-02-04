# -*- coding: utf-8 -*-

import datetime
import pytz
import random
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta

class OrderLine(models.Model):
    _name = 'amgl.order_line'
    _description = 'Order Lines'
    _order = 'create_date desc'

    # region Order Line Create

    @api.model
    def create(self, vals):

        self.validate_quantity_for_creation(vals)

        self.check_deposit_bit_and_update_fields_accordingly(vals)

        mmr_id = vals.get('metal_movement_id')

        cust_id = self.env['amgl.customer'].search([('id', '=', vals['customer_id'])]).custodian_id

        vals['custodian_code'] = self.env['amgl.custodian'].search([('id', '=', cust_id.id)]).custodian_code

        if mmr_id:
            self.update_batch_number_and_quantity_for_mmr_order_line(mmr_id, vals)
        else:
            customer_id, existing_products = self.get_existing_products_against_current_customer(vals)

            if vals['products'] in existing_products:
                self.process_inventory_added_into_existing_product(customer_id, vals)
            else:
                super(OrderLine, self).create(vals)
                vals['is_master_records'] = True

        record = super(OrderLine, self).create(vals)

        if mmr_id:
            self.deduct_quantity_from_current_product(record)

        if not mmr_id: # No need to update customer first deposit date in case of withdrawal.
            self.update_customer_first_deposit_date(vals)

        self.run_static_queries_to_update_records()

        return record

    def update_customer_first_deposit_date(self, vals):
        customer_id = vals['customer_id']
        first_order_line = self.env['amgl.order_line'].search(
            [('customer_id', '=', customer_id), ('is_master_records', '=', False)],
            order='date_received asc', limit=1)
        if first_order_line:
            customer_first_deposit_date = str(
                datetime.datetime.strptime(first_order_line.date_received, '%Y-%m-%d').strftime("%m/%d/%Y"))

        if customer_first_deposit_date == '':
            customer_first_deposit_date = str(datetime.datetime.strptime('2000-01-01', '%Y-%m-%d').strftime("%m/%d/%Y"))

        self.env.cr.execute("UPDATE amgl_customer set customer_first_deposit_date = '" + customer_first_deposit_date
                            + "' where id = " + str(customer_id))

    def update_customer_first_deposit_date_without_params(self):
        customer_first_deposit_date = ''
        customer_id = self.customer_id.id
        first_order_line = self.env['amgl.order_line'].search(
            [('customer_id', '=', customer_id), ('is_master_records', '=', False)],
            order='date_received asc', limit=1)
        if first_order_line:
            customer_first_deposit_date = str(
                datetime.datetime.strptime(first_order_line.date_received, '%Y-%m-%d').strftime("%m/%d/%Y"))

        if customer_first_deposit_date == '':
            customer_first_deposit_date = str(datetime.datetime.strptime('2000-01-01', '%Y-%m-%d').strftime("%m/%d/%Y"))
        self.env.cr.execute(
            "UPDATE amgl_customer set customer_first_deposit_date = '" + customer_first_deposit_date + "' where id = " + str(
                customer_id))

    def run_static_queries_to_update_records(self):
        self.env.cr.execute("""UPDATE amgl_order_line 
                                    SET transaction_detail_sort_date = date_received
                                    WHERE metal_movement_id is null""")
        self.env.cr.execute("""
            UPDATE amgl_order_line b
            SET transaction_detail_sort_date = a.date_create
            FROM amgl_metal_movement AS a
            WHERE a.id = b.metal_movement_id;
        """)

    def process_inventory_added_into_existing_product(self, customer_id, vals):
        product_id = vals['products']
        master_record = self.env['amgl.order_line'].search([
            '&', ('products', '=', product_id), ('is_master_records', '=', True), ('customer_id', '=', customer_id)])
        if vals.get('is_retained'):
            print('')
            # Update quantity and weight values for retained product in master product
            # new_total_received = float(vals['total_received_quantity'])
            # new_total_weight = float(vals['total_received_quantity'])
            # master_record.write({
            #     'total_received_quantity': new_total_received,
            #     'temp_received_weight': new_total_weight,
            #     'date_received': vals.get('date_received'),
            #     'batch_email_sent': False
            # })
        else:
            new_total_received = master_record.total_received_quantity + float(vals['total_received_quantity'])
            master_record.write({
                'total_received_quantity': new_total_received,
                'date_received': vals.get('date_received'),
                'batch_email_sent': False
            })
        vals['is_master_records'] = False

    def get_existing_products_against_current_customer(self, vals):
        customer_id = vals['customer_id']
        customer_orderlines = self.env['amgl.order_line'].search([('customer_id', '=', customer_id)])
        existing_products = []
        for customer_order_line in customer_orderlines:
            if customer_order_line.products.id not in existing_products:
                existing_products.append(customer_order_line.products.id)
        return customer_id, existing_products

    def update_batch_number_and_quantity_for_mmr_order_line(self, mmr_id, vals):
        order_line = self.env['amgl.order_line'].search([('metal_movement_id', '=', mmr_id)])
        if order_line:
            vals.update({
                'batch_number': order_line[0].batch_number,
                'date_for_customer_metal_activitiy': order_line[0].date_for_customer_metal_activitiy
            })
        vals.update({'total_received_quantity': (0 - (float(vals['quantity'])))})

    @staticmethod
    def check_deposit_bit_and_update_fields_accordingly(vals):
        is_deposit = vals.get(
            'is_deposit_related')  # IF is_deposit_related then it means it's from deposit not from MMR
        if is_deposit:
            vals.update({
                'state': 'completed',
                'date_for_customer_metal_activitiy': vals.get('date_received')
            })

    def deduct_quantity_from_current_product(self, current_record):
        master_record = self.env['amgl.order_line'].search([('customer_id', '=', current_record.customer_id.id),
                                                            ('state', '=', 'completed'),
                                                            ('products', '=', current_record.products.id),
                                                            ('is_master_records', '=', True)])
        if master_record:
            # check if given quantity is less than or equal to the quantity available against customer inventory
            if float(current_record.quantity) <= master_record.total_received_quantity:
                # deduct given amount from product's master record
                result = master_record.total_received_quantity - float(current_record.quantity)
                temp_received_weight = self.calculate_weight(master_record.products, result)
                # Update record in database
                self.env.cr.execute("""
                Update amgl_order_line set 
                total_received_quantity = %s , temp_received_weight = %s where id = %s """,
                                    [float(result), float(temp_received_weight), master_record.id])
            else:
                raise ValidationError(
                    str(current_record.products.goldstar_name) + " quantity cannot be greater than " + str(
                        master_record.total_received_quantity))
        else:
            raise ValidationError(str(current_record.products.goldstar_name) + " not available in the stock!")

    @staticmethod
    def validate_quantity_for_creation(vals):
        if vals.get('total_received_quantity') is not None:
            total_received_quantity = vals.get('total_received_quantity')
            try:
                int(str(total_received_quantity))
            except:
                raise ValidationError("Quantity must be integer.")
            if int(total_received_quantity) <= 0:
                raise ValidationError("Quantity cannot be less than 1")

    # endregion

    # region Order Line Update

    @api.multi
    def write(self, vals):
        self.validate_quantity_update(vals)
        if self.metal_movement_id:
            self.update_order_line_for_mmr(vals)
        return super(OrderLine, self).write(vals)

    def validate_quantity_update(self, vals):
        if vals.get('total_received_quantity') is not None:
            total_received_quantity = str(vals.get('total_received_quantity'))
            if '.' in total_received_quantity:
                res = str(total_received_quantity).split('.')[1]
                total_received_quantity = str(total_received_quantity).split('.')[0]
                if int(res) > 0:
                    raise ValidationError("Quantity must be integer.")
            if total_received_quantity == 'False':
                raise ValidationError("Quantity cannot be less than 1")
            if int(total_received_quantity) <= 0:
                raise ValidationError("Quantity cannot be less than 1")

    def update_order_line_for_mmr(self, vals):
        current_product, current_quantity, product_id = self.get_quantity_product_id_from_vals(vals)
        customer_current_master_product = self.env['amgl.order_line'].search([('customer_id', '=', self.customer_id.id),
                                                                              ('state', '=', 'completed'),
                                                                              ('products', '=', product_id),
                                                                              ('is_master_records', '=', True)])
        if current_quantity or current_product:
            earlier_quantity = int(self.quantity)
            if current_quantity:
                updated_quantity = int(current_quantity)
            else:
                updated_quantity = earlier_quantity
            if int(customer_current_master_product.total_received_quantity + earlier_quantity) < updated_quantity:
                raise ValidationError('Withdrawal quantity cannot be greater than ' + str(
                    customer_current_master_product.total_received_quantity + earlier_quantity))
            if current_quantity and not current_product:
                if -self.total_received_quantity < float(current_quantity):
                    difference = float(current_quantity) + self.total_received_quantity
                    quantity = customer_current_master_product.total_received_quantity - float(difference)
                    self.update_query(quantity, customer_current_master_product.id)
                else:
                    difference = -self.total_received_quantity - float(current_quantity)
                    quantity = customer_current_master_product.total_received_quantity + float(difference)
                    self.update_query(quantity, customer_current_master_product.id)

                earlier_weight = self.total_weight
                updated_weight = self._compute_total_weight_oz_for_product_and_quantity(updated_quantity,
                                                                                        self.products[0].id)
                vals.update({
                    'total_received_quantity': (0 - (float(current_quantity))),
                    'temp_received_weight': updated_weight
                })

                self.update_master_product_weight(updated_weight, earlier_weight, customer_current_master_product)

            if current_product:
                customer_earlier_master_product = self.env['amgl.order_line'].search(
                    [('customer_id', '=', self.customer_id.id),
                     ('state', '=', 'completed'), ('products', '=', self.products.id),
                     ('is_master_records', '=', True)])
                quantity = customer_earlier_master_product.total_received_quantity + (-self.total_received_quantity)
                updated_earlier_master_product_weight = customer_earlier_master_product.temp_received_weight + self.total_weight
                self.update_query_for_weight(updated_earlier_master_product_weight, customer_earlier_master_product.id)
                self.update_query(quantity, customer_earlier_master_product.id)
                if not current_quantity:
                    quantity = customer_current_master_product.total_received_quantity + self.total_received_quantity
                    self.update_query(quantity, customer_current_master_product.id)
                else:
                    quantity = customer_current_master_product.total_received_quantity - float(current_quantity)
                    self.update_query(quantity, customer_current_master_product.id)
                    vals.update({'total_received_quantity': (0 - (float(current_quantity)))})

                updated_current_product_weight = self._compute_total_weight_oz_for_product_and_quantity(
                    updated_quantity, current_product)
                updated_current_master_product_weight = customer_current_master_product.temp_received_weight - updated_current_product_weight
                self.update_query_for_weight(updated_current_master_product_weight, customer_current_master_product.id)

    def get_quantity_product_id_from_vals(self, vals):
        current_quantity = vals.get('quantity')
        current_product = vals.get('products')
        if current_product == self.products.id:
            current_product = False
        if current_product:
            product_id = current_product
        else:
            product_id = self.products.id
        return current_product, current_quantity, product_id

    def update_query(self, quantity, id):
        self.env.cr.execute(
            """ Update amgl_order_line set total_received_quantity = %s WHERE id = %s""", [float(quantity), id])

    def update_query_for_weight(self, weight, id):
        self.env.cr.execute(
            """ Update amgl_order_line set temp_received_weight = %s WHERE id = %s""", [float(weight), id])

    def update_master_product_weight(self, updated_weight, earlier_weight, master_product):
        if updated_weight > earlier_weight:
            diff = float(updated_weight) - float(earlier_weight)
            master_product_updated_weight = master_product.temp_received_weight - diff
        else:
            diff = float(earlier_weight) - float(updated_weight)
            master_product_updated_weight = master_product.temp_received_weight + diff
        self.update_query_for_weight(master_product_updated_weight, master_product.id)

    #endregion

    # region Order Line Delete

    @api.multi
    def unlink(self):
        res = super(OrderLine, self)

        customer_master_product = self.get_order_lines(True)

        child_order_lines = self.get_order_lines(False)

        if self.metal_movement_id:
            self.update_master_product_quantity_incase_of_delete_from_mmr_screen(customer_master_product)

            self.delete_fees_objects_against_order_line(customer_master_product.id)

            return res.unlink()

        for order in child_order_lines:

            self.delete_fees_objects_against_order_line(order.id)

            if order.metal_movement_id:
                self.delete_withdrawals_against_order_line(order)
            else:
                self.env.cr.execute("delete from amgl_order_line where id = " + str(order.id))

            self.update_customer_first_deposit_date_without_params()

        return res.unlink()

    def get_order_lines(self, fetch_master_record):
        return self.env['amgl.order_line'].search(
            [('customer_id', '=', self.customer_id.id),
             ('products', '=', self.products.id),
             ('is_master_records', '=', fetch_master_record)])

    def delete_fees_objects_against_order_line(self, order_id):
        self.env.cr.execute('DELETE from amgl_fees where order_line_id = ' + str(order_id))

    def update_master_product_quantity_incase_of_delete_from_mmr_screen(self, customer_master_product):
        if customer_master_product:
            result = customer_master_product.total_received_quantity + float(self.quantity)
            customer_master_product.write({'total_received_quantity': float(result)})

    def delete_withdrawals_against_order_line(self, order):
        mmr_id = order.metal_movement_id.id
        mmr_object = self.env['amgl.metal_movement'].search([('id', '=', mmr_id)])
        if mmr_object.state != 'completed':
            order_line_attched_with_mmr = self.env['amgl.order_line'].search(
                [('metal_movement_id', '=', mmr_id), ('products', '!=', order.products.id)])
            if not order_line_attched_with_mmr:
                self.env.cr.execute("delete from amgl_metal_movement where id = " + str(mmr_id))
                self.env.cr.execute("delete from amgl_order_line where id = " + str(order.id))

    # endregion

    #region  Helpers & Events

    # Not in use right now but written for future use.
    def calculate_inbound_fees(self, customer_id, vals):
        # this fees should calculate on each deposit not each order_line as there could be multiple order_lines in one deposit.
        customer = self.env['amgl.customer'].search([('id', '=', customer_id)])
        create_date = datetime.datetime.strptime(customer.date_opened, '%Y-%m-%d')
        month_after_create_date = create_date + relativedelta(days=30)
        number_of_days = (datetime.datetime.now() - month_after_create_date).days
        inbound_fees = 0.0
        if 0 < number_of_days <= 30:
            fees_records = self.env['amgl.fees'].search([('customer_id', '=', customer_id)])
            if len(fees_records) == 0:
                inbound_fees = 10.00
        if number_of_days > 30:
            inbound_fees = 10.00

        if inbound_fees > 0.0:
            vals['customer_fees'] = [(0, 0, {
                'inbound_fees': inbound_fees,
                'customer_id': customer_id
            })]

    @api.depends('products', 'quantity', 'total_received_quantity')
    def _calculate_total_weight(self):
        received_weight = remaining_qty = remaining_weight = received_quantity = 0
        for order_line in self:
            total_received = order_line.total_received_quantity
            temp_received_weight = self.calculate_weight(order_line.products, order_line.total_received_quantity)

            if order_line.is_deposit_related is True:
                order_line.update({
                    'temp_received_weight': float(temp_received_weight),
                    'total_received_quantity': float(order_line.total_received_quantity),
                    'state': 'completed'
                })
            else:
                for product in order_line.products:
                    if product.weight_unit == 'oz':
                        received_weight = product.weight_per_piece * total_received
                        remaining_qty = float(order_line.quantity) - total_received
                        remaining_weight = product.weight_per_piece * remaining_qty
                    if product.weight_unit == 'gram':
                        received_weight = (product.weight_per_piece * 0.03215) * total_received
                        remaining_qty = float(order_line.quantity) - total_received
                        remaining_weight = product.weight_per_piece * remaining_qty
                    if product.weight_unit == 'kg':
                        received_weight = (product.weight_per_piece * 32.15) * total_received
                        remaining_qty = float(order_line.quantity) - total_received
                        remaining_weight = (product.weight_per_piece * 32.15) * remaining_qty
                    if product.weight_unit == 'pounds':
                        received_weight = (product.weight_per_piece * 16) * total_received
                        remaining_qty = float(order_line.quantity) - total_received
                        remaining_weight = product.weight_per_piece * remaining_qty
                order_line.update({
                    'total_received_quantity': total_received,
                    'temp_received_weight': temp_received_weight
                })

    @staticmethod
    def calculate_weight(product, quantity):
        total_weight = 0
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
    @api.depends('weight')
    def _compute_total_weight_oz(self):
        total_weight = 0
        for order in self:
            qty = float(order.quantity)
            for product in order.products:
                total_weight = self.calculate_weight(product, qty)
            order.update({
                'total_weight': total_weight
            })

    @api.multi
    @api.depends('products', 'quantity')
    def _compute_weight_by_piece(self):
        total_weight = 0
        for order in self:
            for product in order.products:
                if product.weight_unit == 'oz':
                    total_weight = product.weight_per_piece
                if product.weight_unit == 'gram':
                    total_weight = product.weight_per_piece * 0.03215
                if product.weight_unit == 'kg':
                    total_weight = product.weight_per_piece * 32.15
                if product.weight_unit == 'pounds':
                    total_weight = product.weight_per_piece * 16
            order.update({
                'weight': total_weight
            })

    def _compute_total_weight_oz_for_product_and_quantity(self, quantity, product_id):
        qty = float(quantity)
        product = self.env['amgl.products'].search([('id', '=', product_id)])
        return self.calculate_weight(product, qty)

    @api.multi
    @api.depends('products')
    def _get_commodity_from_product(self):
        for order_line in self:
            order_line.update({
                'commodity': order_line.products.type
            })

        # endregion

    @api.one
    @api.depends("products", "total_received_quantity")
    def _update_is_admin_according_to_user_role(self):
        if self.env.user.has_group('amgl.group_amark_admins') or self.env.user.has_group('amgl.group_amark_sub_admins'):
            self.is_admin = True
        else:
            self.is_admin = False

    @api.multi
    def on_change_customer(self, customer):
        if not customer:
            customer = 0
        self.update({
            'quantity': 0
        })
        self.env.cr.execute(
            "select p.* from amgl_order_line as ol inner join amgl_products as p on p.id = ol.products "
            "and ol.state = 'completed' where ol.is_master_records = True and ol.total_received_quantity > 0 and "
            "ol.customer_id =  " + str(customer))
        customer_products = self.env.cr.fetchall()
        product_ids = []
        for item in list(customer_products):
            product_ids.append(item[0])
        return {'domain': {'products': [('id', 'in', product_ids)]}}

    def _get_current_user_role(self):
        if self.env.user.has_group('amgl.group_amark_admins'):
            self.update({'user_role': 'Admin'})
        if self.env.user.has_group('amgl.group_amark_custodian'):
            self.update({'user_role': 'Custodian'})
        if self.env.user.has_group('amgl.group_amark_sub_admins'):
            self.update({'user_role': 'SubAdmin'})
        if self.env.user.has_group('amgl.group_amark_vault'):
            self.update({'user_role': 'Vault'})

    def _update_first_deposit_date(self):
        customer_order_lines = self.env['amgl.order_line'].search(
            ['&', ('customer_id', '=', self.customer_id), ('is_master_records', '=', False)], order='date_received asc')
        self.first_deposit_date = customer_order_lines[0].date_received

    def _get_total_days_from_first_deposit(self):
        customer_order_lines = self.env['amgl.order_line'].search(
            ['&', ('customer_id', '=', self.customer_id), ('is_master_records', '=', False)], order='date_received asc')
        first_deposit_date = customer_order_lines[0].date_received

        end_of_period = first_deposit_date + relativedelta(days=45)

        if datetime.datetime.now() > end_of_period:
            self.deposit_bonus_days_remaining = 'Bonus Time Passed !!'

        if datetime.datetime.now() < end_of_period:
            self.deposit_bonus_days_remaining = str(end_of_period - datetime.datetime.now()).split(',')[
                                                    0] + ' remaining'
        if datetime.datetime.now() == end_of_period:
            self.deposit_bonus_days_remaining = 'Last Day of bonus period.'

    def validate_order_line(self,ol):
        if not ol.metal_movement_id or (ol.metal_movement_id and ol.metal_movement_id.state == 'completed'):
            return True
        else:
            return False

    #endregion

    # region Order Line Notes

    @api.multi
    def add_notes(self):
        view_id = self.env.ref('amgl.order_line_form_view').id
        return {
            'name': ' ',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            "views": [[view_id, "form"]],
            'res_model': 'amgl.order_line',
            'res_id': self.id,
            'target': 'new',
            'flags': {'initial_mode': 'edit', 'options': {'create': False}},
            'context': {
                'show_footer': True
            }
        }

    def launch_notes_wizard(self):
        return {
            'name': 'Add Notes',
            'type': 'ir.actions.act_window',
            'res_model': 'amgl.order_line_notes',
            'src_model': 'amgl.customer',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'user_role': self.user_role
            }
        }

    def save_notes(self):
        if self.notes.encode('ascii', 'ignore') == '<p><br></p>':
            self.write({'notes_boolean': False})
        else:
            self.write({'notes_boolean': True})
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    # endregion

    # region PDF generation related methods

    def download_mmr_pdf(self):
        if 'W' in self.batch_number:
            mmr = self.env['amgl.metal_movement'].search([('id', '=', self.metal_movement_id.id)], limit=1).ids
            data_object = {
                'ids': mmr,
                'model': 'amgl.metal_movement',
                'form': mmr
            }
            return {
                'type': 'ir.actions.report.xml',
                'report_name': 'amgl.report_metalmovement_backend',
                'datas': data_object,
            }
        else:
            order_lines = self.env['amgl.order_line'].search([('is_master_records', '=', False),
                                                              ('batch_number', '=', self.batch_number)])
            order_line_ids = []
            for order in order_lines:
                order_line_ids.append(order.id)
            data_object = {
                'ids': order_line_ids,
                'model': 'amgl.order_line',
                'form': order_line_ids
            }
            return {
                'type': 'ir.actions.report.xml',
                'report_name': 'amgl.customer_orderlines_batch_report',
                'datas': data_object,
                'target': 'current'
            }

    def show_deposit_pdf(self):
        order_lines = self.env['amgl.order_line'].search(
            ['&', ('is_master_records', '=', False), ('batch_number', '=', self.batch_number)])
        order_line_ids = []
        for order in order_lines:
            order_line_ids.append(order.id)
        data_object = {
            'ids': order_line_ids,
            'model': 'amgl.order_line',
            'form': order_line_ids
        }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'amgl.customer_orderlines_batch_report',
            'datas': data_object,
            'target': 'current'
        }

    # endregion

    #region Deposit Batch Methods

    def launch_email_wizard(self):
        return {
            'name': 'Send Email For Deposit Batch',
            'type': 'ir.actions.act_window',
            'res_model': 'amgl.deposit.email.wizard',
            'src_model': 'amgl.customer',
            'view_mode': 'form',
            'target': 'new'
        }

    def update_email_indicator_for_batch(self):
        self.env.cr.execute("""Update amgl_order_line set batch_email_sent = True where batch_number = %s """,
                            [str(self.batch_number)])
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    #endregion

    #region Order Line Batch Report Helpers

    def get_product_total_quantity(self, product, customer, batch_number):

        order_line = self.env['amgl.order_line'].search(
            [('batch_number', '=', batch_number), ('is_master_records', '=', False), ('products', '=', product.id),
             ('customer_id', '=', customer.id)], limit=1)
        if order_line.merged_notes:
            existing_batch_number = order_line.merged_notes.split(' ')[3][1:]
            existing_order_lines = self.env['amgl.order_line'].search(
                [('merged_notes', '=', order_line.merged_notes)])
            order_line_records_merged_into = self.env['amgl.order_line'].search(
                [('batch_number', '=', existing_batch_number), ('products', '=', product.id),
                 ('customer_id', '=', customer.id), ('is_master_records', '=', False)])
            total = 0
            for item in existing_order_lines:
                total += item.total_received_quantity
            return total + order_line_records_merged_into.total_received_quantity
        else:
            return order_line.total_received_quantity

    def get_product_total_weight(self, product, customer, batch_number):
        order_line = self.env['amgl.order_line'].search(
            [('batch_number', '=', batch_number), ('is_master_records', '=', False), ('products', '=', product.id),
             ('customer_id', '=', customer.id)], limit=1)
        if order_line.merged_notes:
            existing_batch_number = order_line.merged_notes.split(' ')[3][1:]
            existing_order_lines = self.env['amgl.order_line'].search(
                [('merged_notes', '=', order_line.merged_notes)])
            order_line_records_merged_into = self.env['amgl.order_line'].search(
                [('batch_number', '=', existing_batch_number), ('products', '=', product.id),
                 ('customer_id', '=', customer.id), ('is_master_records', '=', False)])
            total = 0
            for item in existing_order_lines:
                total += item.temp_received_weight
            return total + order_line_records_merged_into.temp_received_weight
        else:
            return order_line.temp_received_weight

    #endregion

    name = fields.Char()
    notes = fields.Html(string='Product Notes')
    notes_boolean = fields.Boolean(default=False)
    date_received = fields.Date('Date Received',
                                default=lambda self: datetime.datetime.now(pytz.timezone('US/Pacific')))
    products = fields.Many2one('amgl.products', string="Products", required=True)
    product_code = fields.Char(string='Amark Code', related='products.product_code', store=True)  # Field used in import
    gs_product_code = fields.Char(string='Custodian Code', related='products.gs_product_code', store=True)
    weight_per_piece = fields.Float(string='Weight Per Piece', related='products.weight_per_piece', store=True)
    weight_unit = fields.Selection(string='Weight Unit', related='products.weight_unit', store=True)
    commodity = fields.Char(string="Commodity", readonly=True, store=True, compute="_get_commodity_from_product")
    metal_movement_id = fields.Many2one('amgl.metal_movement', string="Meta Movement Reference")
    total_received_quantity = fields.Float(string="Total Received Quantity")
    temp_received_weight = fields.Float(string="Total Received Weight", default=0,
                                        compute='_calculate_total_weight', readonly=True, store=True)
    quantity = fields.Char(string="Expected Quantity")
    weight = fields.Float(readonly=True, string="Weight", required=False, compute="_compute_weight_by_piece",
                          store=True)
    total_weight = fields.Float(readonly=True, string="Expected Quantity Weight", compute="_compute_total_weight_oz",
                                store=True)
    is_deposit_related = fields.Boolean(default=False)
    orderline_history = fields.One2many('amgl.order.history', 'orderline_id', string='Order Lines History')

    is_admin = fields.Boolean(compute="_update_is_admin_according_to_user_role")
    customer_id = fields.Many2one('amgl.customer', string='Customer Name',
                                  default=lambda self: self._context.get('customer_id', False))
    account_number = fields.Char(string="Account Number", readonly=True,
                                 default=lambda self: self._context.get('account_number', False))
    account_type = fields.Char(string="Account Type", readonly=True,
                               default=lambda self: self._context.get('account_type', False))
    custodian_id = fields.Char(string="Custodian", readonly=True,
                               default=lambda self: self._context.get('custodian_id', False))
    dealer_id = fields.Many2one('amgl.dealer', string="Dealer")
    state = fields.Selection([('expecting', 'Expecting'), ('pending', 'Pending'), ('reject', 'Rejected'),
                              ('withdrawal', 'Withdrawal'), ('cancel', 'Cancelled'), ('completed', 'Completed'),
                              ('waiting', 'Waiting For Approval'), ('in_progress', 'In Progress')], 'Status',
                             default='in_progress', readonly=True)
    vault = fields.Char(string='Vault location', default='AMGL')
    custodian_code = fields.Char(default='GST')
    transaction_number = fields.Char(default=random.randint(0, 689651651651))
    transaction_type = fields.Selection([('PR', 'PR'), ('PS', 'PS'), ], default='PR')
    transaction_description = fields.Char()
    show_footer = fields.Boolean(string='Show Footer', default=lambda self: self._context.get('show_footer', False))
    is_master_records = fields.Boolean(default=False)
    customer_fees = fields.One2many('amgl.fees', 'order_line_id', string='Fees')
    date_created = fields.Date(default=datetime.datetime.now().date())
    new_inventory_email_sent = fields.Boolean(default=False)
    batch_number = fields.Char()
    mmr_number = fields.Char()
    batch_email_sent = fields.Boolean(default=False)
    is_active = fields.Boolean(default=True)
    date_for_customer_metal_activitiy = fields.Date()
    user_role = fields.Char(compute=_get_current_user_role)
    first_deposit_date = fields.Date(string='First Deposit Date', compute='_update_first_deposit_date')
    deposit_bonus_days_remaining = fields.Char(string='Bonus Days Remainng',
                                               compute='_get_total_days_from_first_deposit')
    merged_notes = fields.Char()
    customer_account_number = fields.Char(string='Customrt Account Number', related='customer_id.account_number',
                                          store=True)
    transaction_detail_sort_date = fields.Date(string='Metal Movement/OrderLine Create Date')
    order_line_notes_id = fields.Many2one('amgl.order_line_notes', string='Order Line Notes Id')
    bb_location = fields.Char(string='Location')
    bb_brand = fields.Many2one('amgl.product.brands', string="Brands")
    bb_serial_number = fields.Char(string='Serial Number')
    bb_purity = fields.Float(default=0.9990, string='Purity')
    bb_fine_troy = fields.Float(string='Fine Troy Oz')
