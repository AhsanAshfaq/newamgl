# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class OrderLineNotes(models.Model):
    _name = 'amgl.order_line_notes'
    _description = 'Order Line Notes'

    def process_extra_notes(self):
        notes_to_delete = self.env['amgl.order_line_notes'].search([('allow_delete', '=', True)])
        for item in notes_to_delete:
            self.env.cr.execute(" delete from amgl_order_line_notes where id = "+ str(item.id))

    @api.model
    def create(self, vals):
        selected_product_notes = []
        if not vals.get('batches'):
            raise ValidationError('Please select batch number to add notes!')
        master_ol_id = self._context.get('active_id')
        current_order_line = self.env['amgl.order_line'].search([('id', '=', master_ol_id)])
        child_order_line = self.env['amgl.order_line'].search(
            [('customer_id', '=', current_order_line.customer_id.id), ('products', '=', current_order_line.products.id),
             ('is_master_records', '=', False), ('batch_number', '=', str(vals['batches']))])
        if child_order_line:
            selected_product_notes = self.env['amgl.order_line_notes'].search(
                [('customer_id', '=', current_order_line.customer_id.id)
                    , ('batches', '=', str(vals['batches']))
                    , ('orderline_id', '=', child_order_line.id)])
        record = super(OrderLineNotes, self).create(vals)
        if selected_product_notes:
            self.env.cr.execute("""
                                          Update amgl_order_line_notes set customer_id = %s,
                                          orderline_id = %s, product_id = %s, notes = %s
                                          WHERE id = %s""",
                                [current_order_line.customer_id.id, child_order_line.id, current_order_line.products.id,
                                 str(vals['notes']), selected_product_notes.id])
            self.env.cr.execute(" Update amgl_order_line_notes set allow_delete=True where id = " + str(record['id']))
        else:
            self.env.cr.execute("""
                                          Update amgl_order_line_notes set customer_id = %s,
                                          orderline_id = %s, product_id = %s
                                          WHERE id = %s""",
                                [current_order_line.customer_id.id, child_order_line.id, current_order_line.products.id,
                                 record['id']])

        if record['notes'].encode('ascii', 'ignore') != '<p><br></p>':
            self.update_notes_indicator(child_order_line.id, True)
            self.update_notes_indicator(master_ol_id, True)
        else:
            self.update_notes_indicator(child_order_line.id, False)
            self.update_notes_indicator(master_ol_id, False)

        return record

    def save_notes(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def update_notes_indicator(self, ol_id, notes_boolean):
        self.env.cr.execute("""
                                 Update amgl_order_line set notes_boolean = %s
                                 WHERE id = %s""", [notes_boolean, ol_id])

    @api.one
    @api.depends('notes')
    def _get_order_line_batches(self):
        ol_id = self._context.get('active_id')
        if ol_id:
            current_order_line = self.env['amgl.order_line'].search([('id', '=', ol_id)])
            same_product_order_lines = self.env['amgl.order_line'].search(
                [('is_active', '=', True), ('customer_id', '=', current_order_line.customer_id.id),
                 ('products', '=', current_order_line.products.id),
                 ('is_master_records', '=', False), ('metal_movement_id', '=', False)])
            self.product_order_lines = same_product_order_lines
        return True

    @api.onchange('batches')
    def on_change_batches(self):
        ol_id = self._context.get('active_id')
        current_order_line = self.env['amgl.order_line'].search([('id', '=', ol_id)])
        child_order_line = self.env['amgl.order_line'].search(
            [('customer_id', '=', current_order_line.customer_id.id), ('products', '=', current_order_line.products.id),
             ('is_master_records', '=', False), ('batch_number', '=', self.batches)])
        if self.batches:
            order_line_notes = self.env['amgl.order_line_notes'].search(
                [('batches', '=', self.batches),('allow_delete', '=', False), ('orderline_id', '=', child_order_line.id),
                 ('product_id', '=', child_order_line.products.id)])
            self.update({
                'add_notes_clicked': True,
                'notes': order_line_notes.notes
            })
        else:
            self.update({
                'add_notes_clicked': False
            })

    @api.multi
    @api.depends('product_order_lines')
    def get_selection_items(self):
        ol_id = self._context.get('active_id')
        if ol_id:
            current_order_line = self.env['amgl.order_line'].search([('id', '=', ol_id)])
            same_product_order_lines = self.env['amgl.order_line'].search(
                [('is_active', '=', True), ('customer_id', '=', current_order_line.customer_id.id),
                 ('products', '=', current_order_line.products.id),
                 ('is_master_records', '=', False), ('metal_movement_id', '=', False)])
            if same_product_order_lines:
                batch_numbers = []
                for item in same_product_order_lines:
                    batch_number = str(item.batch_number)
                    batch_numbers.append((batch_number, batch_number))
                return batch_numbers

    def _disable_save_button(self):
        if self.env.user.has_group('amgl.group_amark_custodian'):
            self.update({'user_role': True})

    customer_id = fields.Many2one('amgl.customer', string='Customer Name')
    notes = fields.Html(string='Product Notes')
    product_order_lines = fields.One2many('amgl.order_line', 'customer_id',
                                          compute="_get_order_line_batches")
    orderline_id = fields.Integer()
    product_id = fields.Integer()
    add_notes_clicked = fields.Boolean(default=False, Store=False)
    batches = fields.Selection(selection=get_selection_items, string='Select Batch')
    allow_delete = fields.Boolean(default=False)
    user_role = fields.Char(default=lambda self: self._context.get('user_role'))
